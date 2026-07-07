"""Logging utilities for ETL pipeline."""

import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger

def setup_logger(name, log_file=None, level="INFO"):
	"""Setup logger with JSON formatting."""
	logger = logging.getLogger(name)
	logger.setLevel(getattr(logging, level))
	
	formatter = jsonlogger.JsonFormatter(
		"%(timestamp)s %(level)s %(name)s %(message)s"
	)
	
	# Console handler
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	logger.addHandler(console_handler)
	
	# File handler (if log_file provided)
	if log_file:
		file_handler = logging.FileHandler(log_file)
		file_handler.setFormatter(formatter)
		logger.addHandler(file_handler)
	
	return logger
