"""
CrewAI MINT Integration
=======================
Earn MINT tokens for CrewAI crew execution via FoundryNet.

Your crew works. Your crew earns.

Usage:
    from crewai_mint import MintCrewBase
    from crewai import Crew
    
    crew = Crew(agents=[...], tasks=[...])
    mint_crew = MintCrewBase(crew, keypair_path="~/.config/solana/id.json")
    result = mint_crew.kickoff()

Links:
    - GitHub: https://github.com/foundrynet
    - Dashboard: https://foundrynet.github.io/foundry_net_MINT/
"""

from .callback import MintCrewBase, MintSettler, mint_task

__version__ = "1.0.0"
__all__ = ["MintCrewBase", "MintSettler", "mint_task"]
