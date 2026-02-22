# Contributing to Aquilia

First off, thank you for considering contributing to Aquilia! It's people like you that make Aquilia such a great tool.

Below are the guidelines and steps to contribute to the project.

## Code of Conduct
This project and everyone participating in it is governed by the [Aquilia Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Submitting Contributions

### 1. Find an Issue to Work On
Check our [issue tracker](https://github.com/axiomchronicles/aquilia/issues) on GitHub. Issues labeled `good first issue` or `help wanted` are great places to start.

### 2. Fork & Branch
Fork the repository on GitHub and clone it locally. Then, create a new branch for your work:

```bash
git checkout -b feature/your-feature-name
```
or 
```bash
git checkout -b bugfix/your-bugfix-name
```

### 3. Local Development Setup
Aquilia requires Python 3.10 or higher.
We recommend using a virtual environment:

```bash
python -m venv env
source env/bin/activate  # On Windows use `env\Scripts\activate`
```

Install the dependencies, including the development ones:
```bash
pip install -e ".[dev,mlops-all]"
```

### 4. Making Changes
Make your code changes, following our style guides.
* Aquilia adopts standard Python PEP 8 style formatting.
* We recommend using `black` and `ruff` for linting/formatting.
* Ensure all your changes are typed properly.

### 5. Testing
Before submitting, run our test suite using `pytest`:

```bash
pytest tests/
```
Ensure all tests pass and consider adding new tests to cover any new logic or edge cases you introduce. Use `pytest --cov=aquilia` to check coverage.

### 6. Submit a Pull Request
Push your branch to your forked repository and submit a Pull Request against the `master` branch.
Provide a clear description of the problem your PR solves or feature it adds.

## Reporting Bugs
- Make sure you are on the latest version of Aquilia.
- Provide a clear and descriptive title.
- Describe the exact steps which reproduce the problem in as many details as possible.
- Include Python version, OS platform, and any relevant traceback errors.

## Requesting Features
- Outline the proposed feature, the problem it solves, and why it's useful to the broader ecosystem.
- Discuss potential alternatives or existing workarounds if applicable.
