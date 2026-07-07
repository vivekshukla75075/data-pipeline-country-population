"""Configuration module for ETL pipeline."""

import yaml
import os
from pathlib import Path

class Config:
	"""Load and manage configuration from YAML file."""
	
	def __init__(self, config_file=None):
		if config_file is None:
			config_file = os.path.join(
				os.path.dirname(__file__),
				"config.yaml"
			)
		
		with open(config_file, "r") as f:
			self.config = yaml.safe_load(f)
	
	def get(self, key, default=None):
		"""Get configuration value by dot-notation key."""
		keys = key.split(".")
		value = self.config
		for k in keys:
			if isinstance(value, dict):
				value = value.get(k)
			else:
				return default
		return value if value is not None else default

# Global config instance
_config = None

def get_config():
	"""Get global config instance."""
	global _config
	if _config is None:
		_config = Config()
	return _config
