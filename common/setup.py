from setuptools import setup, find_packages

setup(
    name="ai-identity-common",
    version="0.1.0",
    description="Shared library for AI Identity — models, auth, config, schemas",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "sqlalchemy>=2.0",
        "pydantic>=2.0",
        "pydantic-settings>=2.0",
        "python-dotenv>=1.0",
    ],
)
