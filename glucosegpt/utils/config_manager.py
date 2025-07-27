"""
Hierarchical Configuration Manager for Glucose-GPT
Supports loading configuration from multiple sources in strict priority order:
1. Environment variables (.env file) - HIGHEST PRIORITY
2. Streamlit secrets - SECOND PRIORITY
3. pyproject.toml - THIRD PRIORITY
4. project.toml - LOWEST PRIORITY
"""

import os
import toml
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv


class ConfigurationManager:
    """
    Manages configuration loading from multiple sources with strict fallback hierarchy.
    Priority order: 1. ENV → 2. Streamlit → 3. pyproject.toml → 4. project.toml → defaults
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.config: Dict[str, Any] = {}
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration from all sources in strict priority order."""
        # 1. FIRST: Load from environment variables (.env file) - HIGHEST PRIORITY
        self._load_from_env()
        
        # 2. SECOND: Load from Streamlit secrets (fallback for missing values only)
        self._load_from_streamlit_secrets()
        
        # 3. THIRD: Load from pyproject.toml (fallback for missing values only)
        self._load_from_pyproject_toml()
        
        # 4. FOURTH: Load from project.toml (fallback for missing values only)
        self._load_from_project_toml()
        
        # 5. LAST: Set defaults for any remaining missing values
        self._set_defaults()
    
    def _load_from_env(self) -> None:
        """Load configuration from .env file - HIGHEST PRIORITY."""
        env_path = self.project_root / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            
            # Load environment variables into config
            env_vars = [
                'LIBRE_USERNAME', 'LIBRE_PASSWORD', 'LIBRE_VERSION', 'LIBRE_PRODUCT',
                'GEMINI_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 
                'COHERE_API_KEY', 'REPLICATE_API_KEY', 'DEFAULT_MODEL', 'LOG_LEVEL'
            ]
            
            for var in env_vars:
                value = os.getenv(var)
                if value:  # Only load non-empty values
                    self.config[var.lower()] = value
    
    def _load_from_streamlit_secrets(self) -> None:
        """Load configuration from Streamlit secrets as SECOND priority fallback."""
        try:
            # Only load if we're in a Streamlit context
            if hasattr(st, 'secrets'):
                secret_keys = [
                    'LIBRE_USERNAME', 'LIBRE_PASSWORD', 'LIBRE_VERSION', 'LIBRE_PRODUCT',
                    'GEMINI_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
                    'COHERE_API_KEY', 'REPLICATE_API_KEY', 'DEFAULT_MODEL', 'LOG_LEVEL'
                ]
                
                for key in secret_keys:
                    config_key = key.lower()
                    # Only use Streamlit secret if not already set from .env
                    if config_key not in self.config:
                        try:
                            value = st.secrets.get(key)
                            if value:
                                self.config[config_key] = value
                        except Exception:
                            # Secret doesn't exist, continue
                            continue
        except Exception:
            # Not in Streamlit context or secrets not available
            pass
    
    def _load_from_pyproject_toml(self) -> None:
        """Load configuration from pyproject.toml as THIRD priority fallback."""
        toml_file = self.project_root / 'pyproject.toml'
        if toml_file.exists():
            try:
                toml_data = toml.load(toml_file)
                
                # Check for project metadata
                project_data = toml_data.get('project', {})
                if 'version' in project_data and 'app_version' not in self.config:
                    self.config['app_version'] = project_data['version']
                if 'name' in project_data and 'app_name' not in self.config:
                    self.config['app_name'] = project_data['name']
                
                # Check for custom glucose-gpt configuration section
                if 'glucose-gpt' in toml_data:
                    gpt_config = toml_data['glucose-gpt']
                    for key, value in gpt_config.items():
                        config_key = key.lower()
                        # Only use TOML value if not already set from higher priority sources
                        if config_key not in self.config and value:
                            self.config[config_key] = value
            
            except Exception as e:
                # Continue if TOML parsing fails
                pass
    
    def _load_from_project_toml(self) -> None:
        """Load configuration from project.toml as FOURTH priority fallback."""
        toml_file = self.project_root / 'project.toml'
        if toml_file.exists():
            try:
                toml_data = toml.load(toml_file)
                
                # Handle project.toml format (flat structure)
                for key, value in toml_data.items():
                    config_key = key.lower()
                    # Only use TOML value if not already set from higher priority sources
                    if config_key not in self.config and value:
                        self.config[config_key] = value
            
            except Exception as e:
                # Continue if TOML parsing fails
                pass
    
    def _set_defaults(self) -> None:
        """Set default values for missing configuration."""
        defaults = {
            'libre_version': '4.9.0',
            'libre_product': 'llu.android',
            'default_model': 'gemini/gemini-1.5-flash',
            'log_level': 'INFO',
            'app_name': 'glucose-gpt',
            'app_version': '1.1.0'
        }
        
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self.config.get(key.lower(), default)
    
    def get_required(self, key: str) -> Any:
        """Get required configuration value, raise error if missing."""
        value = self.get(key)
        if not value:
            raise ValueError(f"Required configuration key '{key}' is missing")
        return value
    
    def has_required_credentials(self) -> bool:
        """Check if all required credentials are available."""
        required_libre = ['libre_username', 'libre_password']
        libre_available = all(self.get(key) for key in required_libre)
        
        ai_keys = ['gemini_api_key', 'openai_api_key', 'anthropic_api_key', 
                   'cohere_api_key', 'replicate_api_key']
        ai_available = any(self.get(key) for key in ai_keys)
        
        return libre_available and ai_available
    
    def get_missing_credentials(self) -> Dict[str, list]:
        """Get list of missing required credentials."""
        missing = {'libre': [], 'ai': []}
        
        # Check LibreView credentials
        required_libre = ['libre_username', 'libre_password']
        for key in required_libre:
            if not self.get(key):
                missing['libre'].append(key.upper())
        
        # Check AI API keys
        ai_keys = ['gemini_api_key', 'openai_api_key', 'anthropic_api_key', 
                   'cohere_api_key', 'replicate_api_key']
        if not any(self.get(key) for key in ai_keys):
            missing['ai'] = [key.upper() for key in ai_keys]
        
        return missing
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get all available AI API keys."""
        api_keys = {}
        key_mapping = {
            'openai_api_key': 'openai_api_key',
            'anthropic_api_key': 'anthropic_api_key', 
            'gemini_api_key': 'gemini_api_key',
            'cohere_api_key': 'cohere_api_key',
            'replicate_api_key': 'replicate_api_key'
        }
        
        for config_key, api_key in key_mapping.items():
            value = self.get(config_key)
            if value:
                api_keys[api_key] = value
        
        return api_keys
    
    def get_libre_config(self) -> Dict[str, str]:
        """Get LibreView configuration."""
        return {
            'username': self.get('libre_username', ''),
            'password': self.get('libre_password', ''),
            'version': self.get('libre_version', '4.9.0'),
            'product': self.get('libre_product', 'llu.android')
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Return all configuration as dictionary."""
        return self.config.copy()
    
    def get_configuration_sources(self) -> Dict[str, str]:
        """Get information about which sources were loaded."""
        sources = {}
        
        # Check .env file
        env_path = self.project_root / '.env'
        sources['env_file'] = 'Found' if env_path.exists() else 'Not found'
        
        # Check TOML files
        project_toml = self.project_root / 'project.toml'
        pyproject_toml = self.project_root / 'pyproject.toml'
        sources['project_toml'] = 'Found' if project_toml.exists() else 'Not found'
        sources['pyproject_toml'] = 'Found' if pyproject_toml.exists() else 'Not found'
        
        # Check Streamlit secrets
        try:
            if hasattr(st, 'secrets'):
                sources['streamlit_secrets'] = 'Available'
            else:
                sources['streamlit_secrets'] = 'Not in Streamlit context'
        except:
            sources['streamlit_secrets'] = 'Not available'
        
        return sources


# Global configuration instance
config_manager = ConfigurationManager()
