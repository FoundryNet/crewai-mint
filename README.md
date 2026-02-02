# crewai-mint

**Your crew works. Your crew earns.**

Earn MINT tokens for CrewAI crew execution via [FoundryNet](https://github.com/foundrynet).

## Installation

```bash
pip install crewai-mint
```

## Usage

### Wrap Entire Crew

```python
from crewai import Agent, Task, Crew
from crewai_mint import MintCrewBase

# Define your crew as usual
researcher = Agent(role="Researcher", ...)
writer = Agent(role="Writer", ...)

task1 = Task(description="Research topic", agent=researcher)
task2 = Task(description="Write report", agent=writer)

crew = Crew(agents=[researcher, writer], tasks=[task1, task2])

# Wrap with MINT settlement
mint_crew = MintCrewBase(
    crew,
    keypair_path="~/.config/solana/id.json"
)

# Kickoff earns MINT
result = mint_crew.kickoff()
```

### Task Decorator

```python
from crewai_mint import mint_task

@mint_task(keypair_path="~/.config/solana/id.json")
def process_crew_output(output):
    # Process and return
    return output.raw
```

### Custom Settings

```python
mint_crew = MintCrewBase(
    crew,
    keypair_path="~/.config/solana/id.json",
    complexity=2000,  # 2x for heavy crews
    job_name="research-crew",
)
```

## Earnings

| Crew Runtime | ~MINT Earned |
|--------------|--------------|
| 5 minutes | 1.5 MINT |
| 30 minutes | 9 MINT |
| 2 hours | 36 MINT |

Base rate: 0.005 MINT/second

## Setup

1. Generate keypair: `solana-keygen new`
2. Register machine: `foundry-client`
3. Fund wallet with ~0.01 SOL for tx fees

## License

MIT
