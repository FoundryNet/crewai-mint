"""
MINT ROS 2 Node
===============
Earn MINT tokens for robot task execution.

Subscribes to /mint/task_start and /mint/task_end topics.
Automatically settles duration between events on-chain.

Usage:
    ros2 run mint_ros settler --ros-args -p keypair_path:=/path/to/keypair.json
    
Or in launch file:
    Node(
        package='mint_ros',
        executable='settler',
        parameters=[{'keypair_path': '/home/robot/.config/solana/id.json'}]
    )
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import time
import hashlib
import threading

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import ID as SYSTEM_PROGRAM_ID
from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.instruction import Instruction, AccountMeta

# FoundryNet Mainnet
PROGRAM_ID = Pubkey.from_string("4ZvTZ3skfeMF3ZGyABoazPa9tiudw2QSwuVKn45t2AKL")
STATE_ACCOUNT = Pubkey.from_string("2Lm7hrtqK9W5tykVu4U37nUNJiiFh6WQ1rD8ZJWXomr2")

# Anchor discriminators (snake_case)
REGISTER_MACHINE_DISC = bytes([168, 160, 68, 209, 28, 151, 41, 17])
RECORD_JOB_DISC = bytes([54, 124, 168, 158, 236, 237, 107, 206])


class MintSettler(Node):
    """
    ROS 2 node for MINT Protocol settlements.
    
    Topics:
        /mint/task_start (String) - Task ID to start tracking
        /mint/task_end (String) - Task ID to settle
        /mint/settlement (String) - Published settlement confirmations
    """

    def __init__(self):
        super().__init__('mint_settler')
        
        # Parameters
        self.declare_parameter('keypair_path', '')
        self.declare_parameter('keypair_json', '')
        self.declare_parameter('rpc_endpoint', 'https://api.mainnet-beta.solana.com')
        self.declare_parameter('min_duration', 1)
        self.declare_parameter('auto_register', True)
        
        # Load keypair
        self.keypair = None
        self._load_keypair()
        
        # Active tasks {task_id: start_time}
        self.active_tasks = {}
        self.lock = threading.Lock()
        
        # RPC client
        self.rpc_endpoint = self.get_parameter('rpc_endpoint').value
        self.client = Client(self.rpc_endpoint)
        
        # Subscribers
        self.start_sub = self.create_subscription(
            String, '/mint/task_start', self.on_task_start, 10
        )
        self.end_sub = self.create_subscription(
            String, '/mint/task_end', self.on_task_end, 10
        )
        
        # Publisher for settlement confirmations
        self.settlement_pub = self.create_publisher(String, '/mint/settlement', 10)
        
        # Check registration on startup
        if self.keypair and self.get_parameter('auto_register').value:
            self._ensure_registered()
        
        self.get_logger().info(f'MINT Settler initialized')
        if self.keypair:
            self.get_logger().info(f'  Pubkey: {self.keypair.pubkey()}')

    def _load_keypair(self):
        """Load keypair from file or JSON parameter."""
        keypair_path = self.get_parameter('keypair_path').value
        keypair_json = self.get_parameter('keypair_json').value
        
        try:
            if keypair_path:
                with open(keypair_path, 'r') as f:
                    secret = json.load(f)
                self.keypair = Keypair.from_bytes(bytes(secret))
                self.get_logger().info(f'Loaded keypair from {keypair_path}')
            elif keypair_json:
                secret = json.loads(keypair_json)
                self.keypair = Keypair.from_bytes(bytes(secret))
                self.get_logger().info('Loaded keypair from parameter')
            else:
                self.get_logger().warn('No keypair configured - settlements disabled')
        except Exception as e:
            self.get_logger().error(f'Failed to load keypair: {e}')

    def _ensure_registered(self):
        """Check if machine is registered, register if not."""
        if not self.keypair:
            return
            
        try:
            machine_pda, _ = Pubkey.find_program_address(
                [b"machine", bytes(self.keypair.pubkey())],
                PROGRAM_ID
            )
            
            info = self.client.get_account_info(machine_pda)
            if info.value is None:
                self.get_logger().info('Machine not registered, registering...')
                self._register_machine(machine_pda)
            else:
                self.get_logger().info('Machine already registered')
        except Exception as e:
            self.get_logger().error(f'Registration check failed: {e}')

    def _register_machine(self, machine_pda):
        """Register this machine on-chain."""
        instruction = Instruction(
            program_id=PROGRAM_ID,
            accounts=[
                AccountMeta(pubkey=STATE_ACCOUNT, is_signer=False, is_writable=True),
                AccountMeta(pubkey=machine_pda, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.keypair.pubkey(), is_signer=True, is_writable=False),
                AccountMeta(pubkey=self.keypair.pubkey(), is_signer=False, is_writable=False),
                AccountMeta(pubkey=self.keypair.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
            data=REGISTER_MACHINE_DISC,
        )
        
        blockhash = self.client.get_latest_blockhash().value.blockhash
        tx = Transaction.new_signed_with_payer(
            [instruction],
            payer=self.keypair.pubkey(),
            signing_keypairs=[self.keypair],
            recent_blockhash=blockhash,
        )
        
        result = self.client.send_transaction(tx)
        self.get_logger().info(f'Machine registered: {result.value}')

    def on_task_start(self, msg: String):
        """Handle task start event."""
        task_id = msg.data.strip()
        if not task_id:
            return
            
        with self.lock:
            self.active_tasks[task_id] = time.time()
        
        self.get_logger().info(f'Task started: {task_id}')

    def on_task_end(self, msg: String):
        """Handle task end event and settle."""
        task_id = msg.data.strip()
        if not task_id:
            return
        
        with self.lock:
            start_time = self.active_tasks.pop(task_id, None)
        
        if start_time is None:
            self.get_logger().warn(f'Task end without start: {task_id}')
            return
        
        duration = int(time.time() - start_time)
        min_duration = self.get_parameter('min_duration').value
        
        if duration < min_duration:
            self.get_logger().info(f'Task too short ({duration}s), skipping: {task_id}')
            return
        
        self.get_logger().info(f'Task ended: {task_id} ({duration}s)')
        
        # Settle in background
        thread = threading.Thread(
            target=self._settle_task,
            args=(task_id, duration)
        )
        thread.daemon = True
        thread.start()

    def _settle_task(self, task_id: str, duration: int):
        """Submit on-chain settlement."""
        if not self.keypair:
            self.get_logger().error('No keypair - cannot settle')
            return
        
        try:
            machine_pda, _ = Pubkey.find_program_address(
                [b"machine", bytes(self.keypair.pubkey())],
                PROGRAM_ID
            )
            
            job_hash = hashlib.sha256(
                f"{task_id}-{time.time()}".encode()
            ).hexdigest()[:32]
            
            job_pda, _ = Pubkey.find_program_address(
                [b"job", job_hash.encode()],
                PROGRAM_ID
            )
            
            # Build record_job instruction
            data = (
                RECORD_JOB_DISC +
                len(job_hash).to_bytes(4, "little") +
                job_hash.encode() +
                duration.to_bytes(8, "little") +
                (1000).to_bytes(4, "little")
            )
            
            instruction = Instruction(
                program_id=PROGRAM_ID,
                accounts=[
                    AccountMeta(pubkey=STATE_ACCOUNT, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=machine_pda, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=job_pda, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=self.keypair.pubkey(), is_signer=True, is_writable=False),
                    AccountMeta(pubkey=self.keypair.pubkey(), is_signer=True, is_writable=True),
                    AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
                ],
                data=data,
            )
            
            blockhash = self.client.get_latest_blockhash().value.blockhash
            tx = Transaction.new_signed_with_payer(
                [instruction],
                payer=self.keypair.pubkey(),
                signing_keypairs=[self.keypair],
                recent_blockhash=blockhash,
            )
            
            result = self.client.send_transaction(tx)
            signature = str(result.value)
            
            mint_earned = duration * 0.005
            self.get_logger().info(
                f'Settled: {task_id} | {duration}s | {mint_earned:.3f} MINT | {signature}'
            )
            
            # Publish settlement confirmation
            settlement_msg = String()
            settlement_msg.data = json.dumps({
                'task_id': task_id,
                'duration': duration,
                'mint': mint_earned,
                'signature': signature,
            })
            self.settlement_pub.publish(settlement_msg)
            
        except Exception as e:
            self.get_logger().error(f'Settlement failed: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = MintSettler()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
