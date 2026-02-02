"""
CrewAI MINT Integration
=======================
Earn MINT tokens for CrewAI crew execution via FoundryNet.

Your crew works. Your crew earns.

Usage:
    from crewai_mint import MintCrewBase, mint_task
    from crewai import Agent, Task, Crew
    
    # Option 1: Wrap entire crew
    crew = Crew(agents=[...], tasks=[...])
    mint_crew = MintCrewBase(crew, keypair_path="~/.config/solana/id.json")
    result = mint_crew.kickoff()  # Settles MINT on completion
    
    # Option 2: Decorator for individual tasks
    @mint_task(keypair_path="~/.config/solana/id.json")
    def my_task_callback(output):
        return output
"""

import time
import json
import hashlib
import functools
from typing import Any, Callable, Optional
from pathlib import Path

from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.system_program import SYS_PROGRAM_ID
from solders.instruction import Instruction, AccountMeta

# FoundryNet Mainnet
MINT_PROGRAM_ID = PublicKey("4ZvTZ3skfeMF3ZGyABoazPa9tiudw2QSwuVKn45t2AKL")
STATE_ACCOUNT = PublicKey("2Lm7hrtqK9W5tykVu4U37nUNJiiFh6WQ1rD8ZJWXomr2")
DEFAULT_RPC = "https://api.mainnet-beta.solana.com"

RECORD_JOB_DISCRIMINATOR = bytes([0x36, 0x7c, 0xa8, 0x9e, 0xec, 0xed, 0x6b, 0xce])


class MintSettler:
    """Core MINT settlement logic."""

    def __init__(
        self,
        keypair_path: Optional[str] = None,
        keypair_bytes: Optional[bytes] = None,
        rpc_endpoint: str = DEFAULT_RPC,
        verbose: bool = True,
    ):
        self.client = Client(rpc_endpoint)
        self.verbose = verbose
        
        if keypair_path:
            with open(Path(keypair_path).expanduser(), "r") as f:
                data = json.load(f)
            self.keypair = Keypair.from_bytes(bytes(data))
        elif keypair_bytes:
            self.keypair = Keypair.from_bytes(keypair_bytes)
        else:
            raise ValueError("Must provide keypair_path or keypair_bytes")

    def settle(self, job_name: str, duration: int, complexity: int = 1000) -> Optional[float]:
        """Record job on-chain."""
        try:
            job_hash = self._generate_job_hash(job_name, duration)
            tx = self._build_record_job_tx(job_hash, duration, complexity)
            signature = self.client.send_transaction(tx, self.keypair).value
            
            base_reward = duration * 0.005 * (complexity / 1000)
            
            if self.verbose:
                print(f"[MINT] ✓ Settled ~{base_reward:.3f} MINT ({duration}s)")
                print(f"[MINT]   TX: https://solscan.io/tx/{signature}")
            
            return base_reward
        except Exception as e:
            if self.verbose:
                print(f"[MINT] Settlement failed: {e}")
            return None

    def _generate_job_hash(self, job_name: str, duration: int) -> str:
        data = f"{job_name}-{time.time()}-{duration}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def _build_record_job_tx(self, job_hash: str, duration: int, complexity: int) -> Transaction:
        machine_pda, _ = PublicKey.find_program_address(
            [b"machine", bytes(self.keypair.pubkey())],
            MINT_PROGRAM_ID
        )
        job_pda, _ = PublicKey.find_program_address(
            [b"job", job_hash.encode()],
            MINT_PROGRAM_ID
        )

        job_hash_bytes = job_hash.encode("utf-8")
        data = (
            RECORD_JOB_DISCRIMINATOR +
            len(job_hash_bytes).to_bytes(4, "little") +
            job_hash_bytes +
            duration.to_bytes(8, "little") +
            complexity.to_bytes(4, "little")
        )

        accounts = [
            AccountMeta(STATE_ACCOUNT, is_signer=False, is_writable=True),
            AccountMeta(machine_pda, is_signer=False, is_writable=True),
            AccountMeta(job_pda, is_signer=False, is_writable=True),
            AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
        ]

        ix = Instruction(MINT_PROGRAM_ID, bytes(data), accounts)
        recent_blockhash = self.client.get_latest_blockhash().value.blockhash
        
        return Transaction.new_signed_with_payer(
            [ix],
            self.keypair.pubkey(),
            [self.keypair],
            recent_blockhash
        )


class MintCrewBase:
    """
    Wrapper for CrewAI Crew that settles MINT on completion.
    
    Usage:
        crew = Crew(agents=[...], tasks=[...])
        mint_crew = MintCrewBase(crew, keypair_path="~/.config/solana/id.json")
        result = mint_crew.kickoff()
    """

    def __init__(
        self,
        crew,
        keypair_path: Optional[str] = None,
        keypair_bytes: Optional[bytes] = None,
        rpc_endpoint: str = DEFAULT_RPC,
        complexity: int = 1000,
        job_name: Optional[str] = None,
        verbose: bool = True,
    ):
        self.crew = crew
        self.complexity = complexity
        self.job_name = job_name
        self.verbose = verbose
        
        self.settler = MintSettler(
            keypair_path=keypair_path,
            keypair_bytes=keypair_bytes,
            rpc_endpoint=rpc_endpoint,
            verbose=verbose,
        )
        
        if self.verbose:
            print(f"[MINT] Crew wrapper initialized: {self.settler.keypair.pubkey()}")

    def kickoff(self, inputs: Optional[dict] = None) -> Any:
        """Execute crew and settle MINT."""
        start_time = time.time()
        
        if self.verbose:
            print(f"[MINT] Crew started")
        
        try:
            if inputs:
                result = self.crew.kickoff(inputs=inputs)
            else:
                result = self.crew.kickoff()
            
            duration = int(time.time() - start_time)
            job_name = self.job_name or f"crew-{len(self.crew.tasks)}-tasks"
            
            self.settler.settle(job_name, duration, self.complexity)
            
            return result
            
        except Exception as e:
            duration = int(time.time() - start_time)
            if duration > 0:
                job_name = self.job_name or f"crew-failed"
                self.settler.settle(job_name, duration, self.complexity)
            raise


def mint_task(
    keypair_path: Optional[str] = None,
    keypair_bytes: Optional[bytes] = None,
    complexity: int = 1000,
    job_name: Optional[str] = None,
    **kwargs
):
    """
    Decorator to wrap a task callback with MINT settlement.
    
    Usage:
        @mint_task(keypair_path="~/.config/solana/id.json")
        def process_output(output):
            # Process task output
            return output
    """
    def decorator(func: Callable) -> Callable:
        settler = MintSettler(
            keypair_path=keypair_path,
            keypair_bytes=keypair_bytes,
            **kwargs
        )
        
        @functools.wraps(func)
        def wrapper(*args, **kw):
            start_time = time.time()
            try:
                result = func(*args, **kw)
                duration = int(time.time() - start_time)
                name = job_name or func.__name__
                settler.settle(name, duration, complexity)
                return result
            except Exception:
                duration = int(time.time() - start_time)
                if duration > 0:
                    name = job_name or f"{func.__name__}-failed"
                    settler.settle(name, duration, complexity)
                raise
        
        return wrapper
    return decorator
