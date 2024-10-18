```
..
├── moba                                       
│   ├── agent                                       # Main module
│   │   ├── executor.py                                 # Run this to start MobA system
│   │   ├── global_agent.py                             # Global Agent
│   │   ├── local_agent.py                              # Local Agent
│   │   └── plain_agent.py                              # Replace global_agent.py when Plan Module is disabled
│   ├── control                                     # UI controller module
│   │   ├── and_ctrl.py                                 # Android controller module
│   │   └── ctrl.py                                     # Controller template
│   ├── memory                                      # Memory module
│   │   ├── app_memory.py                               # Application memory
│   │   ├── memory.py                                   # Memory template
│   │   ├── task_memory.py                              # Task memory
│   │   └── user_memory.py                              # User memory
│   ├── models                                      # API module
│   │   ├── base.py                                     # Model template
│   │   ├── gemini.py                                   # Google Gemini API
│   │   └── openai.py                                   # OpenAI GPT API
│   ├── process                                     # Information process module
│   │   ├── img_proc.py                                 # Process screenshot
│   │   ├── input_prompter.py                           # Process API prompt
│   │   ├── output_parser.py                            # Parse API response
│   │   └── vh_proc.py                                  # Process VH-tree
│   ├── prompts                                     # Prompt data
│   │   ├── actions.json                                # Action list
│   │   ├── package_list.json                           # App memory by expert
│   │   └── prompts.py                                  # Prompt template
│   ├── utils                                       # Utility module
│   │   ├── android_util.py                             # Connect to the GUI
│   │   ├── config.py                                   # Load configuration file and save configuration and some important data
│   │   ├── logger.py                                   # Save logs
│   │   └── utils.py                                    # Utility functions
│   ├── __init__.py
│   └── config.yaml                                 # Configuration file
└── tools
    ├── ADBKeyboard.apk                             # For typing Unicode content on Android device
    └── aapt-windows
        └── aapt.exe                                    # For extracting APK information                               
```