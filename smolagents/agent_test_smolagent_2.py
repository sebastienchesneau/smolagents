from smolagents import CodeAgent, InferenceClientModel
import numpy as np
import time
import datetime

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


from base import build_model

# Alfred, the butler, preparing the menu for the party
agent = CodeAgent(tools=[], model=build_model(), additional_authorized_imports=['datetime'])

# Preparing the menu for the party
agent.run(
    """
    Alfred needs to prepare for the party. Here are the tasks:
    1. Prepare the drinks - 30 minutes
    2. Decorate the mansion - 60 minutes
    3. Set up the menu - 45 minutes
    4. Prepare the music and playlist - 45 minutes

    If we start right now, at what time will the party be ready?
    """
)