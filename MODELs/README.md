# Model Evaluation Pipeline

A systematic grid search pipeline to evaluate LLM performance across different models, parameters, and extraction tasks.

## 🎯 Overview

This pipeline runs experiments using the **OpenRouter API** to test multiple language models on field extraction tasks. It systematically varies:
- **Models**: GPT-4, Claude, Gemini, etc.
- **Parameters**: Temperature, max_tokens, top_p
- **Fields**: Scheme name, type, eligibility, benefits, etc.

All results are logged to CSV for analysis.

## 📁 Project Structure

```
MODELs/
├── .env.example              # Environment variable template
├── requirements.txt          # Python dependencies
├── experiment_config.py      # Configuration (models, params, fields)
├── openrouter_client.py      # OpenRouter API wrapper
├── run_evaluation.py         # Main execution script
└── evaluation_results.csv    # Output (generated)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd MODELs
pip install -r requirements.txt
```

### 2. Set Up API Key

Create a `.env` file from the template:

```bash
copy .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```
OPENROUTER_API_KEY=your_actual_api_key_here
```

**Get your API key**: https://openrouter.ai/keys

### 3. Configure Experiment

Edit `experiment_config.py` to customize:

- **MODELS**: List of OpenRouter model identifiers
- **TEMPERATURE_VALUES**: Temperature settings to test
- **MAX_TOKENS_VALUES**: Max token limits
- **TOP_P_VALUES**: Nucleus sampling parameters
- **FIELDS_TO_EXTRACT**: Fields to extract from documents

### 4. Run the Pipeline

```bash
python run_evaluation.py
```

## 📊 Output Format

Results are saved to `evaluation_results.csv` with the following columns:

| Column | Description |
|--------|-------------|
| `timestamp` | When the experiment ran |
| `document` | Source document filename |
| `field` | Field being extracted |
| `model` | Model identifier |
| `temperature` | Temperature parameter |
| `max_tokens` | Max tokens parameter |
| `top_p` | Top-p parameter |
| `prompt` | Full prompt sent to model |
| `raw_output` | Model's response |
| `success` | Whether the request succeeded |
| `error` | Error message (if failed) |

## ⚙️ Configuration Options

### Available Models (OpenRouter)

```python
"openai/gpt-4-turbo"
"openai/gpt-3.5-turbo"
"anthropic/claude-3-opus"
"anthropic/claude-3-sonnet"
"google/gemini-pro"
"meta-llama/llama-3-70b-instruct"
```

See full list: https://openrouter.ai/docs#models

### Rate Limiting

Set `RATE_LIMIT_RPM` in `experiment_config.py` to control requests per minute:

```python
RATE_LIMIT_RPM = 60  # 60 requests per minute
```

## 🔧 Customizing Prompts

Prompts are defined in `experiment_config.py` in the `get_extraction_prompt()` function. Modify these to change how fields are extracted.

Example:

```python
"scheme_name": f"""Extract the scheme name from the following document.
Return only the scheme name, nothing else.

Document:
{document_text}

Scheme Name:"""
```

## 📈 Analyzing Results

Load results into pandas for analysis:

```python
import pandas as pd

df = pd.read_csv('evaluation_results.csv')

# Filter successful extractions
successful = df[df['success'] == True]

# Compare models
model_accuracy = successful.groupby('model').size()

# Best temperature per model
best_temp = successful.groupby(['model', 'temperature']).size()
```

## 🎛️ Advanced Usage

### Running a Subset

To test a smaller configuration first, edit `experiment_config.py`:

```python
# Test with just one model
MODELS = ["openai/gpt-3.5-turbo"]

# Test fewer parameter combinations
TEMPERATURE_VALUES = [0.7]
MAX_TOKENS_VALUES = [1000]
```

### Custom Input Folder

Change the input folder in `experiment_config.py`:

```python
INPUT_FOLDER = "/path/to/your/documents"
```

## 🐛 Troubleshooting

**API Key Error**: Make sure `.env` file exists and contains valid `OPENROUTER_API_KEY`

**No Documents Found**: Check that `INPUT_FOLDER` points to the correct directory

**Rate Limit Errors**: Reduce `RATE_LIMIT_RPM` or add delays between batches

**Timeout Errors**: Increase `API_TIMEOUT` in `experiment_config.py`

## 📝 Notes

- Results are appended in real-time to avoid data loss
- Failed requests are logged with error messages
- The pipeline uses exponential backoff for retries
- All prompts and responses are saved for full reproducibility

## 🔗 Resources

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [OpenRouter Models](https://openrouter.ai/docs#models)
- [OpenRouter Pricing](https://openrouter.ai/docs#pricing)
