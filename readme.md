# Deepseek API on Flask

## 🚀 Quick Start

Follow these steps to get the project running on your local machine.

### 1. Clone the repository

### 2. Set up a Virtual Environment

It is highly recommended to use a virtual environment to isolate project dependencies.

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate

```

**Windows:**

```bash
python -m venv venv
.\venv\Scripts\activate

```

### 3. Install Dependencies

Once the virtual environment is activated, install the required packages:

**macOS / Linux:**

```bash
pip3 install -r requirements.txt

```

**Windows:**

```bash
pip install -r requirements.txt

```

### 4. Configure Environment Variables

The project uses a `.env` file for configuration. Create your own by copying the template:

```bash
cp .env.example .env

```

*Note: Open the newly created `.env` file and fill in your actual credentials/API keys.*

### 5. Run the Application

Finally, for example, start the auth project:


```bash
python main.py

```