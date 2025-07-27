from setuptools import setup, find_packages

setup(
	name="glucosegpt",
	version="1.2.0",
	packages=find_packages(include=['glucosegpt', 'glucosegpt.*']),
	install_requires=[
		"requests>=2.32.4",
		"python-dotenv>=1.1.1"
	],
	python_requires=">=3.7",
)
