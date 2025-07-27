# streamlit_app.py
"""
Streamlit application for LibreView glucose data analysis using multiple AI models via LiteLLM.
"""

import os
from typing import Dict, Any, List, Optional, Tuple
import streamlit as st
import pandas as pd
import json
import xml.etree.ElementTree as ET
import plotly.express as px
import plotly.graph_objects as go
import uuid
import litellm
import numpy as np
from glucosegpt.utils.code_runner import CodeRunner
from glucosegpt.clients.libre_view import LibreCGMClient, ApiConfig
from glucosegpt.utils.data_masking import DefaultDataMasker
from glucosegpt.utils.config_manager import config_manager
from glucosegpt.utils.logger import setup_logger

# Set up loggers
console_log, file_log = setup_logger()

class ConfigurationLoader:
	def __init__(self):
		self.console_log = console_log
		self.file_log = file_log

	def load_defaults(self) -> dict:
		"""Load and validate configuration from hierarchical sources."""
		self.file_log.debug("Loading configuration from strict priority hierarchy: .env → TOML → Streamlit secrets")
		
		# Check if required credentials are available
		if not config_manager.has_required_credentials():
			missing = config_manager.get_missing_credentials()
			error_messages = []
			
			if missing['libre']:
				error_messages.append(f"LibreView credentials: {', '.join(missing['libre'])}")
			
			if missing['ai']:
				error_messages.append("At least one AI API key is required")
			
			if error_messages:
				error_msg = "Missing required configuration:\n- " + "\n- ".join(error_messages)
				self.file_log.error(f"Configuration Error - {error_msg}")
				st.error(f"⚠️ {error_msg}")
				
				# Show configuration sources status with priority explanation
				sources = config_manager.get_configuration_sources()
				st.info(f"""
**Configuration Priority System Status:**

🥇 **HIGHEST PRIORITY** - .env file: {sources['env_file']}
🥈 **SECOND PRIORITY** - Streamlit secrets: {sources['streamlit_secrets']}
� **THIRD PRIORITY** - pyproject.toml: {sources['pyproject_toml']}
🏴 **LOWEST PRIORITY** - project.toml: {sources['project_toml']}

⚠️ **IMPORTANT**: The system FIRST searches .env file, then Streamlit secrets, then pyproject.toml, and ONLY uses project.toml as final fallback.

Please configure at least one source with your credentials (preferably .env file).
				""")
				return {}

		# Get configuration from the manager
		libre_config = config_manager.get_libre_config()
		api_keys = config_manager.get_api_keys()
		
		defaults = {
			"libre_username": libre_config['username'],
			"libre_password": libre_config['password'],
			"libre_version": libre_config['version'],
			"libre_product": libre_config['product'],
			"openai_api_key": api_keys.get('openai_api_key', ''),
			"anthropic_api_key": api_keys.get('anthropic_api_key', ''),
			"gemini_api_key": api_keys.get('gemini_api_key', ''),
			"cohere_api_key": api_keys.get('cohere_api_key', ''),
			"replicate_api_key": api_keys.get('replicate_api_key', ''),
			"default_model": config_manager.get('default_model', 'gemini/gemini-1.5-flash')
		}
		
		# Log non-sensitive configuration variables
		non_sensitive = {k: v for k, v in defaults.items() if 'password' not in k and 'key' not in k}
		self.file_log.debug(f"Loaded configuration from priority hierarchy: {non_sensitive}")
		
		# Log which sources provided configuration
		sources = config_manager.get_configuration_sources()
		self.file_log.info(f"Configuration sources priority status: {sources}")
		
		return defaults

class LibreClientManager:
	def __init__(self, email: str, password: str, version: str, product: str):
		self.email = email
		self.password = password
		self.version = version
		self.product = product
		self.client: Optional[LibreCGMClient] = None
		self.connections: List[Dict[str, Any]] = []
		self.session_id = str(uuid.uuid4())
		self.file_log = file_log

	def connect(self) -> bool:
		try:
			self.file_log.info(f"LibreView Connection Attempt - Session: {self.session_id}")
			self.file_log.info(f"Connection Parameters - Version: {self.version}, Product: {self.product}")
			
			config = ApiConfig(version=self.version, product=self.product)
			self.client = LibreCGMClient(
				email=self.email,
				password=self.password,
				config=config,
				data_masker=DefaultDataMasker()
			)
			
			self.file_log.info("Attempting LibreView authentication")
			auth_data = self.client.authenticate()
			self.file_log.info(f"Authentication response status: {auth_data.get('status')}")
			
			if auth_data.get('status') != 0:
				error_msg = f"Authentication failed with status: {auth_data.get('status')}"
				st.toast(error_msg, icon="❌")
				self.file_log.error(error_msg)
				return False
				
			self.file_log.info("Fetching connections list")
			connections_data = self.client.list_connections()
			self.connections = connections_data.get('data', [])
			self.file_log.info(f"Retrieved {len(self.connections)} patient connections")
			
			# Log connection summary (without sensitive data)
			for i, conn in enumerate(self.connections):
				self.file_log.info(f"Connection {i+1}: Patient ID {conn.get('patientId', 'N/A')}, "
								 f"Name: {conn.get('firstName', 'N/A')} {conn.get('lastName', 'N/A')}")
			
			self.file_log.info("Successfully connected to LibreView")
			return True
		except Exception as connection_error:
			error_msg = f"Failed to connect to LibreView: {str(connection_error)}"
			st.toast(error_msg, icon="❌")
			self.file_log.error(error_msg, exc_info=True)
			return False

	def get_patient_data(self, patient_id: str) -> Optional[List[Dict[str, Any]]]:
		try:
			self.file_log.info(f"Fetching glucose data for patient: {patient_id}")
			
			if not self.client:
				self.file_log.error("Client not initialized")
				return None
				
			self.file_log.info("Calling get_patient_graph API")
			graph_data = self.client.get_patient_graph(patient_id)
			
			# Log response structure
			data = graph_data.get('data', {})
			graph_readings = data.get('graphData', [])
			self.file_log.info(f"Retrieved {len(graph_readings)} glucose readings")
			
			if graph_readings:
				first_reading = graph_readings[0] if len(graph_readings) > 0 else {}
				last_reading = graph_readings[-1] if len(graph_readings) > 0 else {}
				self.file_log.info(f"Data range - First: {first_reading.get('Timestamp', 'N/A')}, "
								 f"Last: {last_reading.get('Timestamp', 'N/A')}")
			
			return graph_readings
		except Exception as data_error:
			error_msg = f"Failed to fetch glucose data for patient {patient_id}: {str(data_error)}"
			st.toast(error_msg, icon="❌")
			self.file_log.error(error_msg, exc_info=True)
			return None
 
class DataFormatter:
	@staticmethod
	def process_readings(readings: List[Dict[str, Any]], 
						low_threshold: float, 
						high_threshold: float,
						date_range: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
		processed = []
		seen_timestamps = set()
		
		# Convert date range strings to datetime objects if provided
		start_date = None
		end_date = None
		if date_range and date_range.get('start_date') and date_range.get('end_date'):
			try:
				from datetime import datetime
				start_date = datetime.fromisoformat(date_range['start_date']).date()
				end_date = datetime.fromisoformat(date_range['end_date']).date()
				file_log.info(f"Filtering readings between {start_date} and {end_date}")
			except ValueError as e:
				file_log.error(f"Invalid date format in date range: {e}")
		
		for reading in readings:
			# add to logs the value of reading
			file_log.debug(f"Processing reading: {reading}")
			
			# Remove factory timestamp if it exists
			if 'FactoryTimestamp' in reading:
				del reading['FactoryTimestamp']
				
			timestamp = reading.get('Timestamp')
			if timestamp in seen_timestamps:
				continue
				
			# Apply date filtering if date range is provided
			if start_date and end_date:
				try:
					reading_date = datetime.fromisoformat(timestamp).date()
					if reading_date < start_date or reading_date > end_date:
						file_log.debug(f"Skipping reading from {reading_date} - outside date range")
						continue
				except (ValueError, TypeError) as e:
					file_log.warning(f"Invalid timestamp format: {timestamp} - {e}")
					continue
			
			seen_timestamps.add(timestamp)
			
			try:
				value = float(reading.get('Value', 0))
				reading['isLow'] = value < low_threshold
				reading['isHigh'] = value > high_threshold
			except (ValueError, TypeError):
				reading['isLow'] = False
				reading['isHigh'] = False
			
			if 'MeasureMent' in reading:
				reading['MeasurementType'] = reading.pop('MeasureMent')
				
			processed.append(reading)
		
		return processed

	@staticmethod
	def to_dataframe(readings: List[Dict[str, Any]]) -> pd.DataFrame:
		return pd.DataFrame(readings)

	@staticmethod
	def to_csv(readings: List[Dict[str, Any]]) -> str:
		if not readings:
			return "No data available"
		df = pd.DataFrame(readings)
		return df.to_csv(index=False)

	@staticmethod
	def to_json(readings: List[Dict[str, Any]]) -> str:
		return json.dumps(readings, indent=2)

	@staticmethod
	def to_xml(readings: List[Dict[str, Any]]) -> str:
		root = ET.Element("GlucoseReadings")
		for reading in readings:
			item = ET.SubElement(root, "Reading")
			for key, value in reading.items():
				child = ET.SubElement(item, key)
				child.text = str(value) if value is not None else ""
		return ET.tostring(root, encoding='unicode')

class ChartGenerator:
	@staticmethod
	def create_glucose_chart(readings: List[Dict[str, Any]], chart_type: str, settings: Dict[str, Any]) -> Optional[go.Figure]:
		file_log.info(f"Chart Generation Started - Type: {chart_type}")
		# Log non-sensitive chart settings only
		safe_settings = {k: v for k, v in settings.items() 
						if not any(sensitive in k.lower() for sensitive in ['password', 'key', 'api_key', 'secret'])}
		file_log.debug(f"Chart Settings: {safe_settings}")
		
		if not readings:
			file_log.warning("Chart generation failed: No readings provided")
			return None

		df = pd.DataFrame(readings)
		file_log.debug(f"DataFrame Created - Shape: {df.shape}")
		
		if df.empty:
			file_log.warning("Chart generation failed: Empty DataFrame")
			return None
			
		df['Timestamp'] = pd.to_datetime(df['Timestamp'])
		df = df.sort_values('Timestamp')
		
		# Apply glucose range filtering if enabled
		if settings.get('filter_by_range', False):
			min_val = settings.get('glucose_min', 0)
			max_val = settings.get('glucose_max', 300)
			original_count = len(df)
			df = df[(df['Value'] >= min_val) & (df['Value'] <= max_val)]
			file_log.info(f"Chart filtering: {original_count} → {len(df)} readings")
		
		file_log.info(f"Generating {chart_type} chart with {len(df)} data points")
		
		if chart_type == "line":
			fig = px.line(df, x='Timestamp', y='Value', title='Glucose Levels Over Time')
			fig.update_traces(line=dict(width=2))
		elif chart_type == "scatter":
			fig = px.scatter(df, x='Timestamp', y='Value', title='Glucose Readings Scatter Plot')
		elif chart_type == "bar":
			fig = px.bar(df, x='Timestamp', y='Value', title='Glucose Levels Bar Chart')
		elif chart_type == "histogram":
			fig = px.histogram(df, x='Value', title='Glucose Value Distribution', nbins=30)
		elif chart_type == "box":
			fig = px.box(df, y='Value', title='Glucose Value Distribution Box Plot')
		elif chart_type == "area":
			fig = px.area(df, x='Timestamp', y='Value', title='Glucose Levels Area Chart')
		elif chart_type == "heatmap":
			df['Date'] = df['Timestamp'].dt.date
			df['Time'] = df['Timestamp'].dt.hour
			pivot_df = df.pivot_table(values='Value', index='Time', columns='Date', aggfunc='mean')
			fig = px.imshow(pivot_df, title='Glucose Heatmap (Hour vs Date)')
		else:
			file_log.warning(f"Unsupported chart type: {chart_type}")
			return None
			
		fig.update_layout(
			xaxis_title="Time" if chart_type not in ["histogram", "box", "heatmap"] else "Date" if chart_type == "heatmap" else "",
			yaxis_title="Glucose Level (mg/dL)" if chart_type != "heatmap" else "Glucose Level",
			hovermode="x unified" if chart_type not in ["histogram", "box", "heatmap"] else "closest"
		)
		return fig

class AIAnalyzer:
	def __init__(self, api_keys: Dict[str, str]):
		self.api_keys = api_keys
		if self.api_keys.get("openai_api_key"):
			litellm.openai_key = self.api_keys["openai_api_key"]
		if self.api_keys.get("anthropic_api_key"):
			litellm.anthropic_key = self.api_keys["anthropic_api_key"]
		if self.api_keys.get("gemini_api_key"):
			litellm.gemini_key = self.api_keys["gemini_api_key"]
		if self.api_keys.get("cohere_api_key"):
			litellm.cohere_key = self.api_keys["cohere_api_key"]
		if self.api_keys.get("replicate_api_key"):
			litellm.replicate_key = self.api_keys["replicate_api_key"]
			
	def fix_code(self, code_blocks: List[str], model: str, error_info: str = None) -> Dict[str, Any]:
		"""Fix any issues in the provided code blocks."""
		file_log.info(f"Fixing code with model: {model}")
		file_log.info(f"Number of code blocks to fix: {len(code_blocks)}")
		
		# Log the original code blocks
		for i, block in enumerate(code_blocks):
			file_log.debug(f"Original Code Block {i+1}:\n{block}")
		
		if error_info:
			file_log.info(f"Error information provided: {error_info}")
		
		code_blocks_text = "\n\n".join([f"```python\n{block}\n```" for block in code_blocks])
		
		prompt = "You are an expert Python programmer. I need you to fix any issues in the following code blocks. " \
				"Focus only on fixing errors, improving code quality, and enhancing performance.\n\n" \
				f"Code blocks to fix:\n{code_blocks_text}\n\n"
		
		if error_info:
			prompt += f"Error encountered:\n{error_info}\n\n"
		
		prompt += "Please provide the fixed code. Add comments explaining what you fixed. " \
				 "Return ONLY the fixed code blocks with no additional explanations outside the code blocks. " \
				 "Each code block should be enclosed in ```python and ``` markers."
		
		# Log the complete prompt being sent to LLM
		file_log.info("=== LLM FIX CODE REQUEST ===")
		file_log.info(f"Model: {model}")
		file_log.info(f"Prompt length: {len(prompt)} characters")
		file_log.debug(f"Full prompt:\n{prompt}")
		
		try:
			response = litellm.completion(
				model=model,
				messages=[{"role": "user", "content": prompt}],
				temperature=0.1
			)
			result = response.choices[0].message.content
			
			# Log the LLM response
			file_log.info("=== LLM FIX CODE RESPONSE ===")
			file_log.info(f"Response length: {len(result)} characters")
			file_log.debug(f"Full response:\n{result}")
			
			# Extract fixed code blocks
			fixed_blocks = CodeRunner.extract_code_blocks(result)
			
			file_log.info(f"Extracted {len(fixed_blocks)} fixed code blocks from LLM response")
			for i, block in enumerate(fixed_blocks):
				file_log.debug(f"Fixed Code Block {i+1}:\n{block}")
			
			return {
				"result": result,
				"fixed_blocks": fixed_blocks
			}
			
		except Exception as e:
			error_msg = f"Error fixing code: {str(e)}"
			file_log.error(error_msg, exc_info=True)
			return {
				"error": error_msg
			}

	def analyze(self, readings: List[Dict[str, Any]], query: str, model: str) -> Dict[str, Any]:
		file_log.info(f"Starting AI analysis with model: {model}")
		file_log.debug(f"Analysis Query: {query}")
		
		valid_readings = [r for r in readings if r.get('Value')]
		values = [float(r['Value']) for r in valid_readings]
		
		file_log.debug(f"Data Summary - Total readings: {len(readings)}, Valid readings: {len(valid_readings)}")
		
		if not values:
			file_log.warning("Analysis failed: No valid glucose readings found")
			return {"result": "No valid glucose readings found for analysis.", "has_code": False}
		
		# Check if this is a complex query that might benefit from code execution
		complex_keywords = [
			"code", "script", "function", "calculate", "algorithm", "trend", "correlation", 
			"regression", "statistical", "advanced", "analyze", "plot", "visualization", 
			"distribution", "compute", "complex", "metrics", "time series", "machine learning"
		]
		is_complex = any(keyword in query.lower() for keyword in complex_keywords)
		
		# Create dataframe from readings for code execution
		df = pd.DataFrame(valid_readings)
		if 'Timestamp' in df.columns:
			df['Timestamp'] = pd.to_datetime(df['Timestamp'])
		
		# Prepare the prompt based on query complexity
		if is_complex:
			file_log.info("Detected complex query, requesting Python code")
			prompt = f"""
			You are a medical data analyst specializing in glucose monitoring. You have expertise in Python data analysis.
			
			The user has the following glucose readings available as a pandas DataFrame named 'data':
			
			Data Structure:
			```
			{df.head(5).to_string()}
			```
			
			Data Types:
			```
			{df.dtypes}
			```
			
			Basic Statistics:
			- Number of readings: {len(values)}
			- Average glucose: {sum(values)/len(values):.1f}
			- Minimum: {min(values)}
			- Maximum: {max(values)}
			
			User Query: "{query}"
			
			Generate Python code to analyze this data and answer the query. Your response should include:
			1. An explanation of your approach
			2. Python code using pandas, numpy, and plotly that directly works with the 'data' DataFrame
			3. Code that creates visualizations where appropriate using plotly (NOT matplotlib)
			4. Ensure your code generates clear outputs, tables, and charts that will display properly in Streamlit
			
			Important Guidelines:
			- Use plotly for all visualizations (px.scatter, px.line, px.bar, etc.)
			- Generate DataFrames for tabular results
			- Use print() statements for key insights
			- Your Python code must be enclosed in ```python and ``` markers
			- Do not use plt.show() or matplotlib, as code will be executed in Streamlit
			- Ensure the last line of your code generates a meaningful result (chart, table, or summary)
			"""
		else:
			prompt = f"""
			You are a medical data analyst specializing in glucose monitoring. Here is a set of glucose readings:
			
			Glucose Data:
			{df.head(10).to_string()}
			
			Basic Statistics:
			- Number of readings: {len(values)}
			- Average glucose: {sum(values)/len(values):.1f}
			- Minimum: {min(values)}
			- Maximum: {max(values)}
			
			From User Query "{query}" provide clear and concise output.
			If the user requests a chart, table, or structured format, generate the appropriate visualization code or data structure.
			For charts, use Plotly syntax. For tables, use markdown table format.
			"""
		
		# Log the complete prompt being sent to LLM
		file_log.info("=== LLM ANALYSIS REQUEST ===")
		file_log.info(f"Model: {model}")
		file_log.info(f"Is complex query: {is_complex}")
		file_log.info(f"Prompt length: {len(prompt)} characters")
		file_log.debug(f"Full prompt:\n{prompt}")
		
		file_log.info(f"AI Analysis Request - Model: {model}, Query: {query[:100]}...")
		file_log.info(f"Data Summary - Readings: {len(valid_readings)}, Avg: {sum(values)/len(values):.1f}")
		
		try:
			response = litellm.completion(
				model=model,
				messages=[{"role": "user", "content": prompt}],
				max_tokens=2000,
				temperature=0.3
			)
			result = response.choices[0].message.content
			
			# Log the LLM response
			file_log.info("=== LLM ANALYSIS RESPONSE ===")
			file_log.info(f"Response length: {len(result)} characters")
			file_log.debug(f"Full response:\n{result}")
			
			file_log.info(f"AI Analysis Completed - Response length: {len(result)} characters")
			
			# For complex queries, attempt to run any code blocks
			if is_complex:
				file_log.info("Running code blocks from LLM response")
				code_results = CodeRunner.run_llm_code_blocks(result, {"data": df})
				
				# Log code extraction and execution results
				file_log.info(f"Code execution results - Has code: {code_results['has_code']}")
				if code_results.get('code_blocks'):
					file_log.info(f"Number of code blocks executed: {len(code_results['code_blocks'])}")
					for i, block in enumerate(code_results['code_blocks']):
						file_log.debug(f"Executed Code Block {i+1}:\n{block.get('code', 'No code')}")
						file_log.debug(f"Execution result {i+1}: {block.get('output', 'No output')}")
				
				# Only return code results if there actually was code to execute
				if code_results['has_code']:
					return {
						"result": result,
						"has_code": code_results["has_code"],
						"code_results": code_results,
						"is_complex": True
					}
				else:
					# Complex query but no code found, return as normal analysis
					file_log.info("Complex query detected but no code blocks found in LLM response")
					return {"result": result, "has_code": False, "is_complex": False}
			
			return {"result": result, "has_code": False, "is_complex": False}
		except Exception as model_error:
			error_message = f"Error analyzing data with {model}: {str(model_error)}"
			file_log.error(error_message, exc_info=True)
			return {"result": error_message, "has_code": False, "error": True}

def validate_credentials(username: str, password: str) -> Tuple[bool, str]:
	file_log.info("Starting credentials validation process")
	file_log.debug(f"Validating username: {username[:3]}***{username[-3:] if len(username) > 6 else ''}")
	
	if not username:
		file_log.warning("Username validation failed: Username/email is required")
		file_log.debug("Validation Error - Empty username provided")
		return False, "Username/email is required"
	
	if not password:
		file_log.warning("Password validation failed: Password is required")
		file_log.debug("Validation Error - Empty password provided")
		return False, "Password is required"
	
	if len(password) < 6:
		file_log.warning("Password validation failed: Password too short")
		file_log.debug(f"Validation Error - Password length: {len(password)} (minimum: 6)")
		return False, "Password must be at least 6 characters"
	
	file_log.info("Credentials validation successful")
	file_log.debug("All credential validation checks passed")
	return True, ""

def validate_api_keys(api_keys: Dict[str, str]) -> Tuple[bool, str]:
	file_log.info("Validating API keys")
	# Check if at least one API key is provided
	if not any(api_keys.values()):
		file_log.warning("API key validation failed: No API keys provided")
		return False, "At least one API key is required"
	file_log.info("API key validation successful")
	return True, ""

def show_toast(message: str, success: bool = True):
	icon = "✅" if success else "❌"
	st.toast(message, icon=icon)

def show_configuration_guide():
	"""Display configuration guide when setup is incomplete."""
	st.error("⚠️ Configuration Incomplete")
	
	st.markdown("""
	### 📝 Glucose-GPT Configuration Priority System
	
	**Glucose-GPT follows a strict priority order for configuration:**
	1. 🥇 **Environment File (.env)** - **HIGHEST PRIORITY**
	2. 🥈 **Streamlit Secrets** - **SECOND PRIORITY**
	3. 🥉 **pyproject.toml** - **THIRD PRIORITY**
	4. 🏴 **project.toml** - **LOWEST PRIORITY**
	
	⚠️ **IMPORTANT**: The system will FIRST check .env file, then Streamlit secrets, then pyproject.toml, and ONLY use project.toml as final fallback!
	
	#### 🥇 Method 1: Environment File (.env) - RECOMMENDED
	```bash
	# Create and configure .env file (HIGHEST PRIORITY)
	cp .env.example .env
	# Edit .env file with your credentials
	```
	
	#### 🥈 Method 2: Streamlit Secrets (Second Priority)
	```bash
	# Configure .streamlit/secrets.toml - used if .env is missing values
	LIBRE_USERNAME = "your.email@example.com"
	LIBRE_PASSWORD = "your_password"
	GEMINI_API_KEY = "your_gemini_key"
	```
	
	#### 🥉 Method 3: pyproject.toml (Third Priority)
	```bash
	# Configure pyproject.toml - used if .env and Streamlit are missing values
	[glucose-gpt]
	LIBRE_USERNAME="your.email@example.com"
	LIBRE_PASSWORD="your_password"
	GEMINI_API_KEY="your_gemini_key"
	```
	
	#### 🏴 Method 4: project.toml (Lowest Priority)
	```bash
	# Configure project.toml - only used as final fallback
	LIBRE_USERNAME="your.email@example.com"
	LIBRE_PASSWORD="your_password"
	GEMINI_API_KEY="your_gemini_key"
	```
	
	### 🔑 Required Configuration
	
	**LibreView Credentials (Required)**:
	- `LIBRE_USERNAME`: Your LibreView account email/username
	- `LIBRE_PASSWORD`: Your LibreView account password
	
	**AI Model API Keys (At least one required)**:
	- `GEMINI_API_KEY`: Google's Gemini AI (recommended)
	- `OPENAI_API_KEY`: OpenAI's GPT models
	- `ANTHROPIC_API_KEY`: Anthropic's Claude
	- `COHERE_API_KEY`: Cohere's models
	- `REPLICATE_API_KEY`: Replicate's models
	
	### ⚙️ Optional Settings
	- `LIBRE_VERSION`: API version (default: 4.9.0)
	- `LIBRE_PRODUCT`: Product type (default: llu.android)
	- `DEFAULT_MODEL`: Preferred AI model (default: gemini/gemini-1.5-flash)
	
	### 🔄 Next Steps
	1. **RECOMMENDED**: Use the .env file method (highest priority)
	2. Add your credentials to your chosen configuration source
	3. Restart the application
	
	💡 **Tip**: Always use .env file for maximum compatibility and security!
	""")

def display_support():
	st.markdown("<div style='text-align: center;'>Share and Support</div>", unsafe_allow_html=True)
	
	st.write("""
		<div style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
			<ul style="list-style-type: none; margin: 0; padding: 0; display: flex;">
				<li style="margin-right: 10px;"><a href="https://twitter.com/haseeb_heaven" target="_blank"><img src="https://img.icons8.com/color/32/000000/twitter--v1.png"/></a></li>
				<li style="margin-right: 10px;"><a href="https://www.buymeacoffee.com/haseebheaven" target="_blank"><img src="https://img.icons8.com/color/32/000000/coffee-to-go--v1.png"/></a></li>
				<li style="margin-right: 10px;"><a href="https://www.youtube.com/@HaseebHeaven/videos" target="_blank"><img src="https://img.icons8.com/color/32/000000/youtube-play.png"/></a></li>
				<li><a href="https://github.com/haseeb-heaven/glucose-gpt" target="_blank"><img src="https://img.icons8.com/color/32/000000/github--v1.png"/></a></li>
			</ul>
		</div>
	""", unsafe_allow_html=True)

def main():
	st.set_page_config(page_title="Glucose-GPT - AI Glucose Analytics", layout="wide")
	st.title("🔬 Glucose-GPT - AI Glucose Analytics")
	
	file_log.info("Application started")
	
	# Run comprehensive tests on first launch
	if 'tests_run' not in st.session_state:
		st.session_state.tests_run = True
		
		# Import test runner
		try:
			from glucosegpt.utils.test_runner import TestRunner
			
			with st.spinner("🧪 Running comprehensive test suite..."):
				test_runner = TestRunner()
				tests_passed = test_runner.run_pre_launch_tests()
				
				if not tests_passed:
					st.error("❌ Critical tests failed! Please fix the issues before continuing.")
					st.info("💡 Check the test failure details above and run tests manually to debug.")
					st.stop()  # Stop execution if tests fail
				
				file_log.info("All pre-launch tests passed successfully")
				
		except ImportError as e:
			st.warning(f"⚠️ Could not import test runner: {str(e)}. Continuing without tests.")
			file_log.warning(f"Test runner import failed: {str(e)}")
		except Exception as e:
			st.error(f"❌ Test execution failed: {str(e)}")
			st.info("💡 Please check your test configuration and dependencies.")
			file_log.error(f"Test execution failed: {str(e)}")
			st.stop()  # Stop execution if tests fail critically
	
	config_loader = ConfigurationLoader()
	defaults = config_loader.load_defaults()
	
	if not defaults:
		show_configuration_guide()
		return

	with st.sidebar:
		st.header("⚙️ Configuration")
		
		with st.expander("Account Settings", expanded=True):
			email = st.text_input("LibreView Email", value=defaults["libre_username"])
			password = st.text_input("LibreView Password", value=defaults["libre_password"], type="password")
			
			# Credential validation now happens automatically when saving settings or connecting
			file_log.debug("Credential validation button removed as requested")
		
		with st.expander("AI Model Settings", expanded=True):
			openai_api_key = st.text_input("OpenAI API Key", value=defaults["openai_api_key"], type="password")
			anthropic_api_key = st.text_input("Anthropic API Key", value=defaults["anthropic_api_key"], type="password")
			gemini_api_key = st.text_input("Gemini API Key", value=defaults["gemini_api_key"], type="password")
			cohere_api_key = st.text_input("Cohere API Key", value=defaults["cohere_api_key"], type="password")
			replicate_api_key = st.text_input("Replicate API Key", value=defaults["replicate_api_key"], type="password")
			
			available_models = [
				"gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
				"claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
				"gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash",
				"command-nightly", "command",
				"replicate/meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3"
			]
			
			# Set default index to Gemini Flash
			default_model = defaults.get("default_model", "gemini/gemini-1.5-flash")
			try:
				default_index = available_models.index(default_model)
			except ValueError:
				# If default model not found, use Gemini Flash as fallback
				default_index = available_models.index("gemini/gemini-1.5-flash")
			
			selected_model = st.selectbox(
				"AI Model",
				options=available_models,
				index=default_index,
				help="Select the AI model to use for analysis. Changes take effect after saving settings."
			)
			
			# Show warning for Gemini Pro
			if selected_model == "gemini/gemini-1.5-pro":
				st.warning("⚠️ Gemini Pro has strict rate limits. Consider using Gemini Flash for better availability.")
		
		
		with st.expander("LibreView Settings", expanded=False):
			libre_version = st.text_input("API Version", value=defaults["libre_version"])
			libre_product = st.selectbox(
				"Product",
				options=["llu.ios", "llu.android"],
				index=0 if defaults["libre_product"] == "llu.ios" else 1
			)
		
		with st.expander("Data Display Settings", expanded=False):
			# Data Range Settings
			st.subheader("🗓️ Data Range")
			data_range = st.radio(
				"Select Data Range",
				options=["All Data", "Custom Date Range"],
				horizontal=True
			)
			
			if data_range == "Custom Date Range":
				col1, col2 = st.columns(2)
				with col1:
					start_date = st.date_input("Start Date")
				with col2:
					end_date = st.date_input("End Date")
			
			# Glucose Range Settings
			st.subheader("📊 Glucose Range")
			glucose_min, glucose_max = st.slider(
				"Glucose Range (mg/dL)",
				min_value=0,
				max_value=500,
				value=(70, 180),
				step=1
			)
			st.info(f"Readings below {glucose_min} will be marked as LOW\nReadings above {glucose_max} will be marked as HIGH")
			
			# Data Format Settings
			st.subheader("📋 Display Format")
			data_formats = ["None", "Table", "CSV", "JSON", "XML"]
			selected_format = st.selectbox(
				"Data Format",
				options=data_formats,
				index=0  # Default to None
			)
			
			# Chart settings
			st.subheader("Chart Settings")
			enable_charts = st.checkbox("Enable Chart Generation", value=False)  # Default to disabled
			if enable_charts:
				available_charts = ["None", "line", "scatter", "bar", "histogram", "box", "area", "heatmap"]
				selected_charts = st.multiselect(
					"Chart Types",
					options=available_charts,
					default=["None"]
				)
				filter_by_range = st.checkbox("Filter Charts by Glucose Range", value=False)
			else:
				selected_charts = []
				filter_by_range = False
		
		if st.button("💾 Save Settings"):
			api_keys = {
				"openai_api_key": openai_api_key,
				"anthropic_api_key": anthropic_api_key,
				"gemini_api_key": gemini_api_key,
				"cohere_api_key": cohere_api_key,
				"replicate_api_key": replicate_api_key
			}
			
			is_valid, message = validate_api_keys(api_keys)
			if not is_valid:
				show_toast(message, success=False)
				file_log.warning(f"Settings save failed: {message}")
				return
			
			st.session_state['app_settings'] = {
				'email': email,
				'password': password,
				'libre_version': libre_version,
				'libre_product': libre_product,
				'api_keys': api_keys,
				'selected_model': selected_model,
				'glucose_min': glucose_min,
				'glucose_max': glucose_max,
				'selected_format': selected_format,
				'enable_charts': enable_charts,
				'selected_charts': selected_charts,
				'filter_by_range': filter_by_range,
				'data_range': data_range,
				'date_range': {
					'start_date': start_date.isoformat() if data_range == "Custom Date Range" else None,
					'end_date': end_date.isoformat() if data_range == "Custom Date Range" else None
				}
			}
			
			# Log settings (without sensitive data)
			safe_settings = {k: v for k, v in st.session_state['app_settings'].items() 
						   if not any(sensitive in k.lower() for sensitive in ['password', 'key', 'api_key', 'secret'])}
			file_log.info(f"Settings saved: {safe_settings}")
			show_toast(f"Settings saved! Using AI model: {selected_model}")
			file_log.info(f"AI model set to: {selected_model}")
		
		if st.button("🔄 Connect to LibreView"):
			if 'app_settings' not in st.session_state:
				show_toast("Please save settings first!", success=False)
				file_log.warning("Connection attempt failed: Settings not saved")
				return
				
			settings = st.session_state['app_settings']
			is_valid, message = validate_credentials(settings['email'], settings['password'])
			if not is_valid:
				show_toast(message, success=False)
				file_log.warning(f"Connection validation failed: {message}")
				return
				
			with st.spinner("Connecting to LibreView..."):
				client_manager = LibreClientManager(
					settings['email'], 
					settings['password'], 
					settings['libre_version'], 
					settings['libre_product']
				)
				if client_manager.connect():
					st.session_state['client_manager'] = client_manager
					st.session_state['connections'] = client_manager.connections
					file_log.info("LibreView connection established successfully")
					show_toast("Connected successfully!")
				else:
					show_toast("Failed to connect", success=False)
					file_log.error("LibreView connection failed")
		
		# Add support section at the bottom of sidebar
		st.markdown("---")
		display_support()
	
	if 'client_manager' not in st.session_state:
		st.info("👈 Please configure your settings, save them, and connect to LibreView in the sidebar")
		file_log.info("Waiting for user to configure settings")
		return
	
	client_manager = st.session_state['client_manager']
	connections = st.session_state.get('connections', [])
	settings = st.session_state.get('app_settings', {})
	
	# Fix any existing session state that still uses Gemini Pro
	if settings.get('selected_model') == 'gemini/gemini-1.5-pro':
		settings['selected_model'] = 'gemini/gemini-1.5-flash'
		st.session_state['app_settings'] = settings
		file_log.info("Auto-switched from Gemini Pro to Flash due to rate limits")
		st.info("ℹ️ Automatically switched to Gemini Flash to avoid rate limits.")
	
	if not connections:
		st.warning("No patient connections found")
		file_log.warning("No patient connections available")
		return
	
	patient_names = [conn.get('firstName', 'Unknown') + " " + conn.get('lastName', 'Patient') 
					 for conn in connections]
	selected_patient_idx = st.selectbox(
		"Patient",
		range(len(patient_names)),
		format_func=lambda x: patient_names[x]
	)
	
	selected_connection = connections[selected_patient_idx]
	patient_id = selected_connection.get('patientId')
	
	if not patient_id:
		show_toast("Invalid patient selection", success=False)
		file_log.error("Invalid patient selection")
		return
	
	# Fetch patient data only if not already in session or patient changed
	if ('current_patient_data' not in st.session_state or 
		st.session_state.get('current_patient_id') != patient_id):
		file_log.info(f"Fetching new patient data for ID: {patient_id}")
		with st.spinner("Fetching glucose data..."):
			raw_readings = client_manager.get_patient_data(patient_id)
			if raw_readings:
				formatter = DataFormatter()
				processed_readings = formatter.process_readings(
					raw_readings, 
					settings.get('glucose_min', 70), 
					settings.get('glucose_max', 180),
					settings.get('date_range') if settings.get('data_range') == "Custom Date Range" else None
				)
				st.session_state['current_patient_data'] = processed_readings
				st.session_state['current_patient_id'] = patient_id
				st.session_state['raw_readings'] = raw_readings
				file_log.info(f"Fetched and cached data for patient {patient_id} - {len(raw_readings)} readings")
			else:
				st.warning("No glucose data available for this patient")
				file_log.warning(f"No glucose data available for patient {patient_id}")
				return
	else:
		processed_readings = st.session_state['current_patient_data']
		file_log.debug(f"Using cached patient data for ID: {st.session_state.get('current_patient_id')}")
	
	st.subheader("📊 Glucose Data")
	
	selected_format = settings.get('selected_format', 'None')
	file_log.info(f"Displaying data in {selected_format} format")
	
	if selected_format == "None":
		st.info("Data display is disabled. Select a display format in settings to view the data.")
	elif selected_format == "Table":
		df = DataFormatter.to_dataframe(processed_readings)
		# Format boolean columns to be more readable
		if 'isLow' in df.columns:
			df['isLow'] = df['isLow'].map({True: 'Low', False: 'Normal'})
		if 'isHigh' in df.columns:
			df['isHigh'] = df['isHigh'].map({True: 'High', False: 'Normal'})
		st.dataframe(df, use_container_width=True)
	elif selected_format == "CSV":
		try:
			csv_data = DataFormatter.to_csv(processed_readings)
			st.download_button(
				label="Download CSV",
				data=csv_data,
				file_name="glucose_readings.csv",
				mime="text/csv",
			)
			st.code(csv_data, language="text")
		except Exception as e:
			st.error(f"Failed to generate CSV: {str(e)}")
			file_log.error(f"CSV generation error: {str(e)}", exc_info=True)
	elif selected_format == "JSON":
		try:
			json_data = DataFormatter.to_json(processed_readings)
			st.download_button(
				label="Download JSON",
				data=json_data,
				file_name="glucose_readings.json",
				mime="application/json",
			)
			st.code(json_data, language="json")
		except Exception as e:
			st.error(f"Failed to generate JSON: {str(e)}")
			file_log.error(f"JSON generation error: {str(e)}", exc_info=True)
	elif selected_format == "XML":
		try:
			xml_data = DataFormatter.to_xml(processed_readings)
			st.download_button(
				label="Download XML",
				data=xml_data,
				file_name="glucose_readings.xml",
				mime="application/xml",
			)
			st.code(xml_data, language="xml")
		except Exception as e:
			st.error(f"Failed to generate XML: {str(e)}")
			file_log.error(f"XML generation error: {str(e)}", exc_info=True)
	
	# Chart generation section
	if settings.get('enable_charts', False):
		st.subheader("📈 Glucose Charts")
		selected_charts = settings.get('selected_charts', ['None'])
		
		# Filter out 'None' from the selected charts
		active_charts = [chart for chart in selected_charts if chart != 'None']
		
		if active_charts and processed_readings:
			file_log.info(f"Generating charts: {active_charts}")
			tabs = st.tabs([chart.title() for chart in active_charts])
			
			for i, chart_type in enumerate(active_charts):
				with tabs[i]:
					try:
						fig = ChartGenerator.create_glucose_chart(
							processed_readings, 
							chart_type, 
							settings
						)
						if fig:
							st.plotly_chart(fig, use_container_width=True)
							file_log.info(f"Successfully generated {chart_type} chart")
						else:
							st.warning(f"Could not generate {chart_type} chart")
							file_log.warning(f"Failed to generate {chart_type} chart")
					except Exception as chart_error:
						error_msg = f"Error generating {chart_type} chart: {str(chart_error)}"
						st.warning(error_msg)
						file_log.error(error_msg, exc_info=True)
		elif 'None' in selected_charts and not active_charts:
			st.info("Chart display is disabled. Select chart types in settings to view charts.")
		elif not processed_readings:
			st.info("No data available to generate charts")
			file_log.info("No data available for chart generation")
	else:
		file_log.debug("Chart generation is disabled in settings")

	st.subheader("🧠 Chatbot")

	user_query = st.text_area(
		"Your query about the glucose data",
		height=100,
		placeholder="e.g., What are the average glucose levels? Show me a chart of glucose trends...",
		key="user_query"
	)
	
	# Runtime complex query detection
	is_complex = False
	if user_query:
		complex_keywords = [
			"code", "script", "function", "calculate", "algorithm", "trend", "correlation", 
			"regression", "statistical", "advanced", "analyze", "plot", "visualization", 
			"distribution", "compute", "complex", "metrics", "time series", "machine learning"
		]
		is_complex = any(keyword in user_query.lower() for keyword in complex_keywords)
		
		if is_complex:
			st.info("📊 Complex query detected! Code will be automatically generated, executed, and fixed if needed.")
			file_log.info(f"Complex query detected: {user_query[:100]}...")
	
	# Create three columns for buttons
	col1, col2, col3 = st.columns([1, 1, 1])
	
	# 1. Execute Query button (always visible) - now handles auto-execution for complex queries
	with col1:
		if is_complex:
			execute_query = st.button("🔍 Execute Query", type="primary", 
									help="Will automatically execute and fix any generated code")
		else:
			execute_query = st.button("🔍 Execute Query")
	
	# 2. Run Code button (visible when code is available) - for manual re-execution
	with col2:
		if 'last_code_blocks' in st.session_state and st.session_state['last_code_blocks']:
			run_code_button = st.button("🚀 Run Code", 
									  help="Manually re-execute previously generated code")
		else:
			run_code_button = False
	
	# 3. Fix Code button (visible when code is available) - for manual fixing
	with col3:
		if 'last_code_blocks' in st.session_state and st.session_state['last_code_blocks']:
			fix_code_button = st.button("🔧 Fix Code",
									  help="Manually fix previously generated code")
		else:
			fix_code_button = False
	
	# Process button presses
	if execute_query or run_code_button or fix_code_button:
		if not user_query:
			show_toast("Enter query", success=False)
			file_log.warning("AI analysis failed: Empty query")
			return
			
		if 'app_settings' not in st.session_state:
			show_toast("Settings not found. Please save settings first.", success=False)
			file_log.warning("AI analysis failed: Settings not found")
			return
		
		# Handle regular query execution
		if execute_query:
			settings = st.session_state['app_settings']
			
			# Ensure we use Flash model, not Pro (due to rate limits)
			selected_model = settings.get('selected_model', 'gemini/gemini-1.5-flash')
			if selected_model == 'gemini/gemini-1.5-pro':
				selected_model = 'gemini/gemini-1.5-flash'
				file_log.info("Switched from Gemini Pro to Flash due to rate limits")
			
			with st.spinner(f"Analyzing data with {selected_model}..."):
				file_log.info(f"Starting AI analysis with model: {selected_model}")
				analyzer = AIAnalyzer(settings.get('api_keys', {}))
				analysis_result = analyzer.analyze(processed_readings, user_query, selected_model)
				
				# Store the generated code blocks for future use
				if analysis_result.get("has_code", False):
					st.session_state['last_code_blocks'] = CodeRunner.extract_code_blocks(analysis_result["result"])
				
				st.markdown("### Analysis Results")
				st.markdown(analysis_result["result"])
				
				# Auto-execute code for complex queries with automatic fixing
				if analysis_result.get("has_code", False) and analysis_result.get("is_complex", False):
					st.markdown("### 🚀 Auto-Executing Generated Code")
					
					# Prepare data for code execution
					df = DataFormatter.to_dataframe(processed_readings)
					if 'Timestamp' in df.columns:
						df['Timestamp'] = pd.to_datetime(df['Timestamp'])
					
					code_blocks = CodeRunner.extract_code_blocks(analysis_result["result"])
					max_attempts = 3  # Maximum attempts to fix and execute code
					file_log.info(f"Auto-executing code blocks: {len(code_blocks)} blocks")
					attempt = 1
					
					while attempt <= max_attempts:
						try:
							st.write(f"**Attempt {attempt}/{max_attempts}:**")
							file_log.info(f"Auto-executing code blocks - Attempt {attempt}")
							
							# Execute the code
							code_results = CodeRunner.run_llm_code_blocks(
								"\n\n".join([f"```python\n{block}\n```" for block in code_blocks]), 
								{"data": df}
							)
							
							# Check for errors in execution
							has_errors = any(not block["success"] for block in code_results["executed_blocks"])
							
							if not has_errors:
								# Success! Display results
								st.success(f"✅ Code executed successfully on attempt {attempt}!")
								
								# Store the successful code blocks
								st.session_state['last_code_blocks'] = code_blocks
								
								# Display execution results with enhanced formatting
								CodeRunner.display_streamlit_results(code_results, st)
								
								file_log.info(f"Auto-execution successful on attempt {attempt}")
								
								# Show summary
								if attempt > 1:
									st.info(f"🎯 **Auto-Execution Summary:** Successfully executed after {attempt} attempts with AI-powered fixes!")
								
								break  # Success, exit the loop
							
							else:
								# There are errors, try to fix them
								error_blocks = [block for block in code_results["executed_blocks"] if not block["success"]]
								st.warning(f"⚠️ Errors detected in {len(error_blocks)} code block(s). Attempting to fix...")
								
								# Show the errors
								for i, block in enumerate(error_blocks):
									st.error(f"Error in block {i+1}: {block['output']}")
								
								if attempt < max_attempts:
									# Try to fix the code using AI
									with st.spinner("🔧 AI is fixing the code..."):
										file_log.info(f"Attempting to fix code errors - Attempt {attempt}")
										
										# Collect error details for the LLM
										error_details = []
										for i, block in enumerate(error_blocks):
											error_details.append(f"Error in block {i+1}: {block['output']}")
										error_info = "\n".join(error_details)
										
										fix_result = analyzer.fix_code(code_blocks, selected_model, error_info)
										
										if 'error' not in fix_result and 'fixed_blocks' in fix_result:
											code_blocks = fix_result['fixed_blocks']
											st.info(f"🔧 Code fixed by AI. Retrying execution...")
											file_log.info("Code fixed by AI, retrying execution")
											
											# Update stored code blocks with fixed version
											st.session_state['last_code_blocks'] = code_blocks
										else:
											st.error(f"❌ AI failed to fix the code: {fix_result.get('error', 'Unknown error')}")
											file_log.error(f"AI failed to fix code: {fix_result.get('error', 'Unknown error')}")
											break
								else:
									st.error(f"❌ Failed to execute code after {max_attempts} attempts")
									file_log.error(f"Failed to execute code after {max_attempts} attempts")
						
						except Exception as execution_error:
							error_msg = f"Execution error on attempt {attempt}: {str(execution_error)}"
							st.error(error_msg)
							file_log.error(error_msg, exc_info=True)
							
							if attempt < max_attempts:
								st.info("🔧 Attempting to fix the error...")
								# Try to fix using the error message
								try:
									file_log.info(f"Attempting to fix execution exception - Attempt {attempt}")
									file_log.error(f"Exception details: {str(execution_error)}")
									
									fix_result = analyzer.fix_code(code_blocks, selected_model, str(execution_error))
									if 'error' not in fix_result and 'fixed_blocks' in fix_result:
										code_blocks = fix_result['fixed_blocks']
										st.session_state['last_code_blocks'] = code_blocks
										st.info("Code fixed, retrying...")
										file_log.info("Code fixed after exception, retrying")
									else:
										st.error("Failed to fix code after exception")
										file_log.error("Failed to fix code after exception")
										break
								except Exception as fix_error:
									st.error(f"Failed to fix code: {str(fix_error)}")
									file_log.error(f"Failed to fix code after exception: {str(fix_error)}", exc_info=True)
									break
							else:
								st.error(f"❌ Failed after {max_attempts} attempts")
						
						attempt += 1
				elif analysis_result.get("is_complex", False) and not analysis_result.get("has_code", False):
					st.info("🔍 Complex query detected, but no executable code was generated by the AI. This is a text-based analysis.")
				
				file_log.info("AI analysis completed successfully")
		
		# Handle code execution
		elif run_code_button:
			settings = st.session_state['app_settings']
			if 'last_code_blocks' in st.session_state and st.session_state['last_code_blocks']:
				with st.spinner("Running generated code..."):
					file_log.info("Executing previously generated code blocks")
					
					# Prepare data for code execution
					df = DataFormatter.to_dataframe(processed_readings)
					if 'Timestamp' in df.columns:
						df['Timestamp'] = pd.to_datetime(df['Timestamp'])
					
					# Use the correct method name
					code_results = CodeRunner.run_llm_code_blocks(
						"\n\n".join([f"```python\n{block}\n```" for block in st.session_state['last_code_blocks']]), 
						{"data": df}
					)
					
					st.markdown("### Code Execution Results")
					
					# Use enhanced display method
					CodeRunner.display_streamlit_results(code_results, st)
					
					file_log.info("Code execution completed successfully")
			else:
				show_toast("No code available to run. Execute a complex query first.", success=False)
				file_log.warning("Code execution failed: No code blocks available")
		
		# Handle code fixing
		elif fix_code_button:
			settings = st.session_state['app_settings']
			if 'last_code_blocks' in st.session_state and st.session_state['last_code_blocks']:
				# Ensure we use Flash model, not Pro (due to rate limits)
				selected_model = settings.get('selected_model', 'gemini/gemini-1.5-flash')
				if selected_model == 'gemini/gemini-1.5-pro':
					selected_model = 'gemini/gemini-1.5-flash'
					file_log.info("Switched from Gemini Pro to Flash for code fixing due to rate limits")
				
				with st.spinner("Fixing code with AI..."):
					file_log.info("Manual code fixing initiated")
					analyzer = AIAnalyzer(settings.get('api_keys', {}))
					
					# Provide general improvement instruction for manual fixes
					improvement_note = "Please improve code quality, add error handling, optimize performance, and enhance readability."
					fix_result = analyzer.fix_code(st.session_state['last_code_blocks'], selected_model, improvement_note)
					
					if 'error' not in fix_result:
						st.markdown("### 🔧 Fixed Code")
						st.markdown(fix_result["result"])
						
						# Store the fixed code blocks
						if 'fixed_blocks' in fix_result:
							st.session_state['last_code_blocks'] = fix_result['fixed_blocks']
							show_toast("Code fixed successfully!")
							file_log.info("Manual code fixing completed successfully")
						else:
							show_toast("No code blocks found in fix result", success=False)
							file_log.warning("Manual code fixing: No code blocks in result")
					else:
						st.error(f"Error fixing code: {fix_result['error']}")
						file_log.error(f"Manual code fixing failed: {fix_result['error']}")
			else:
				show_toast("No code available to fix. Execute a complex query first.", success=False)
				file_log.warning("Manual code fixing failed: No code blocks available")

if __name__ == "__main__":
	try:
		main()
	except Exception as application_error:
		error_msg = f"Application error: {str(application_error)}"
		st.toast(error_msg, icon="❌")
		file_log.critical(error_msg, exc_info=True)
		raise