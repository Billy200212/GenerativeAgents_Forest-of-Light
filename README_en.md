[简体中文](./README.md) | English

# Generative Agents: Forest of Light Edition

This project is based on the [Generative Agents](https://github.com/joonspk-research/generative_agents) project, open-sourced by Stanford University and Google in August 2023, which simulates realistic human life through AI.

Building upon [GenerativeAgentsCN](https://github.com/x-glacier/GenerativeAgentsCN.git)(a Chinese version of Generative Agents), this project updates maps and characters, optimizes the replay interface, and introduces the new "Forest of Light" version. It is equipped with a story outline to test the degree of AI alignment within game narratives.
## 1. Preparation

### 1.1 Get the Code：

```
git clone https://github.com/x-glacier/GenerativeAgentsCN.git
cd GenerativeAgentsCN
```

### 1.2 Configure Large Language Model (LLM)

Modify the configuration file `generative_agents/data/config.json`:
1. By default, it uses [Ollama](https://ollama.com/) to load local quantized models and provides an OpenAI-compatible API. You need to pull the quantized model first (refer to [ollama.md](docs/ollama.md)) and ensure that base_url and model match your Ollama configuration.
2. If you wish to call other OpenAI-compatible APIs, change the`provider`to`openai`，and modify the `model`、`api_key`和`base_url`and base_url according to the API documentation.

### 1.3 Install Python Dependencies

It is recommended to create and activate a virtual environment using anaconda3 first:

```
conda create -n generative_agents_cn python=3.12
conda activate generative_agents_cn
```

Install dependencies:

```
pip install -r requirements.txt
```

## 2. Run Virtual Town

```
cd generative_agents
python start.py --name sim-test --start "20250213-09:30" --step 10 --stride 10
```

Parameter description:
- `name` - Sets a unique name for the simulation start, used for later replay.
- `start` - The starting time of the virtual town.
- `resume` - Continues running the virtual town from the last "checkpoint" after a finished run or accidental interruption.
- `step` - Stops running after a certain number of iteration steps.
- `stride` - The time (in minutes) in the virtual town corresponding to each iteration step. If set to `--stride 10`, the time changes during iteration will be 9:00, 9:10, 9:20...

## 3. Replay

### 3.1 Start Replay Service

```
python compress.py --name <simulation-name>
```
After execution, a replay data file `movement.json` will be generated in the `results/compressed/<simulation-name>` directory. A `simulation.md` file will also be generated, presenting each agent's status and dialogue content in a timeline format.

### 3.2 Start Replay Service

```
python replay.py
```

Open the replay page in your browser (address: `http://127.0.0.1:5000/?name=<simulation-name>`) to observe the residents' activities in the virtual town during various time periods.

Controls:  
- `Middle Mouse Button/Arrow Keys` - Pan the view。
- `Mouse Wheel` - Zoom the map.
- `Enter` - Play/Pause.
- `Bottom Character Bar` - Click any character to lock the camera on them.

## 4. Modify Map
`jiejieje`has developed a map annotation tool for this project. Project address: https://github.com/jiejieje/tiled_to_maze.json

## 5. References

### 5.1 Papers

[Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)

### 5.2 Code

[Generative Agents](https://github.com/joonspk-research/generative_agents)

[wounderland](https://github.com/Archermmt/wounderland)

[GenerativeAgentsCN](https://github.com/x-glacier/GenerativeAgentsCN.git)