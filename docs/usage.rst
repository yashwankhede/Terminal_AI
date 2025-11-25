Usage
=====

Basic Usage
-----------

.. code-block:: bash

   terminal-ai "list all files in current directory"

Interactive Mode
----------------

.. code-block:: bash

   terminal-ai --interactive

Python API
----------

.. code-block:: python

   from terminal_ai import ask_ai_for_commands, execute_commands_sequence
   
   commands = ask_ai_for_commands("your prompt", api_key="your-key")
   execute_commands_sequence(commands, api_key="your-key")

