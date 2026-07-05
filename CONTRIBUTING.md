# Contributing to AgentForge

Thank you for your interest in contributing! This document outlines the process for contributing to the project.

## Code of Conduct

Be respectful, constructive, and collaborative. Harassment of any kind will not be tolerated.

## How to Contribute

### Reporting Bugs
- Use GitHub Issues with the "Bug" template
- Include: steps to reproduce, expected vs actual behavior, environment details
- Attach relevant logs or screenshots

### Suggesting Features
- Open a "Feature Request" issue
- Describe the problem and proposed solution
- Discuss with maintainers before implementing

### Pull Request Process
1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Follow the coding style:
   - TypeScript: Prettier + ESLint (configs in repo)
   - Python: Black + isort + flake8
4. Write tests for new functionality
5. Update documentation if needed
6. Ensure CI passes
7. Submit PR with clear description

## Development Setup
```bash
git clone https://github.com/lanekingkong/agentforge.git
cd agentforge
npm install
pip install -r requirements.txt
npm run dev
```

## Commit Convention
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Adding tests
- `chore:` Maintenance

## Questions?
Open a GitHub Discussion or contact the maintainers.

---

**Thanks for contributing!**
