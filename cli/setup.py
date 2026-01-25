from setuptools import setup, find_packages

setup(
    name="fhir-eval",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "requests>=2.31.0",
        "anthropic>=0.17.0",
        "python-dotenv>=1.0.0",
        "rich>=13.7.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=5.1.0",
        "selenium>=4.16.0",
        "webdriver-manager>=4.0.1",
    ],
    entry_points={
        "console_scripts": [
            "fhir-eval=fhir_eval.main:cli",
        ],
    },
)
