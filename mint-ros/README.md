# MINT ROS 2

Earn **MINT tokens** for robot task execution.

## How It Works

1. Robot starts task → publish to `/mint/task_start`
2. Robot completes task → publish to `/mint/task_end`
3. Settler node calculates duration and settles on-chain
4. MINT earned → 0.005 MINT per second

## Installation

```bash
cd ~/ros2_ws/src
git clone https://github.com/foundrynet/mint-ros
cd ..
pip install solders solana base58
colcon build --packages-select mint_ros
source install/setup.bash
```

## Usage

### Start the settler node

```bash
ros2 run mint_ros settler --ros-args -p keypair_path:=/path/to/keypair.json
```

Or with launch file:

```bash
ros2 launch mint_ros settler.launch.py keypair_path:=/home/robot/.config/solana/id.json
```

### Emit task events from your robot code

```python
from std_msgs.msg import String

# In your robot node
self.mint_start_pub = self.create_publisher(String, '/mint/task_start', 10)
self.mint_end_pub = self.create_publisher(String, '/mint/task_end', 10)

# When task starts
msg = String()
msg.data = 'pick_object_42'
self.mint_start_pub.publish(msg)

# When task completes
msg = String()
msg.data = 'pick_object_42'
self.mint_end_pub.publish(msg)
```

### Test with fake tasks

```bash
# Run settler in one terminal
ros2 run mint_ros settler --ros-args -p keypair_path:=/path/to/keypair.json

# In another terminal, run test task
ros2 run mint_ros test_task --ros-args -p duration:=10
```

## Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/mint/task_start` | `std_msgs/String` | Publish task ID to start tracking |
| `/mint/task_end` | `std_msgs/String` | Publish task ID to settle |
| `/mint/settlement` | `std_msgs/String` | Settlement confirmations (JSON) |

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `keypair_path` | `` | Path to Solana keypair JSON |
| `keypair_json` | `` | Keypair as JSON string (alternative) |
| `rpc_endpoint` | `mainnet-beta` | Solana RPC URL |
| `min_duration` | `1` | Minimum seconds to settle |
| `auto_register` | `true` | Auto-register machine on startup |

## Earning Rate

- **Base rate:** 0.005 MINT per second
- **1 minute task:** 0.3 MINT
- **1 hour task:** 18 MINT

## Requirements

- ROS 2 (Humble/Iron/Jazzy)
- Python 3.8+
- Funded Solana wallet (~0.001 SOL per settlement)

---

**MINT Protocol** — Wages for Machines
