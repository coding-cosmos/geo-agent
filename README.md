# 🌍 Geo-Agent

**Geo-Agent** is an intelligent, AI-driven geospatial analysis tool that leverages the power of **Google Earth Engine (GEE)** and the **Gemini API** to autonomously plan, execute, and synthesize complex geospatial analyses.

By bridging large language models with petabyte-scale satellite imagery datasets, Geo-Agent can interpret user questions, formulate an analytical plan, execute data extractions (e.g., NDVI, Landcover), validate the results, and generate a natural language synthesis of its findings.

---

## ✨ Features

- **🧠 Autonomous Planning:** Uses Gemini to break down natural language queries into specific, actionable geospatial analysis steps.
- **🛰️ Google Earth Engine Integration:** Seamlessly interfaces with GEE for processing large-scale satellite data like Sentinel-2 and ESA WorldCover.
- **🌱 NDVI Analysis:** Calculates vegetation indices and computes regional statistics over custom Areas of Interest (AOIs).
- **🗺️ Landcover Analysis:** Determines landcover compositions (trees, water, built-up areas, etc.) for a given region.
- **✅ Built-in Validation:** Automatically assesses the quality of the data (e.g., cloud cover limits, usable image counts) before presenting findings.
- **💬 Intelligent Synthesis:** Synthesizes raw numerical data into human-readable, evidence-backed conclusions.

---

## 📋 Prerequisites

Before running Geo-Agent, ensure you have the following:

1. **Python 3.10+**
2. **Google Cloud Project** with the [Google Earth Engine API enabled](https://developers.google.com/earth-engine/guides/access).
3. **Earth Engine Access:** Your local environment or service account must be authenticated with GEE.
4. **Gemini API Key:** An active API key from Google AI Studio.

---

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/coding-cosmos/geo-agent.git
   cd geo-agent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory based on `.env.example`:
   ```env
   GEE_PROJECT_ID=your-google-cloud-project-id
   GEMINI_API_KEY=your-gemini-api-key
   ```

4. **Authenticate with Google Earth Engine:**
   If running locally for the first time, authenticate your machine:
   ```bash
   earthengine authenticate
   ```

---

## 💻 Usage

You can run the provided example in `main.py` to see a sample NDVI analysis pipeline in action:

```bash
python main.py
```

This script will:
1. Initialize Google Earth Engine.
2. Define a rectangular Area of Interest (AOI).
3. Execute the `ndvi_tool` over the specified dates.
4. Print the findings, data quality metrics, methodology, and limitations.
5. Print the automated validation score of the analysis.

---

## 🏗️ Project Structure

- `app/agent/`: Core Gemini integration (planning, reasoning, and synthesis).
- `app/analysis/`: Raw geospatial analysis logic (NDVI, Landcover) using `ee`.
- `app/models/`: Pydantic models for structured outputs, plans, and validation schemas.
- `app/tools/`: Tool wrappers that adapt the analysis logic for the Gemini agent.
- `app/gee.py`: Earth Engine initialization and authentication logic.
- `tests/`: Comprehensive pytest suite.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. When contributing, please ensure that your code passes the existing test suite:

```bash
pytest tests/
```

