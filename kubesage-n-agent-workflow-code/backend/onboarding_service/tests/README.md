# Onboarding Service Tests

This directory contains comprehensive test suites for the KubeSage onboarding service.

## Test Structure

### 📁 Test Files

- **`test_onboarding.py`** - Unit tests for core onboarding functionality
  - Cluster onboarding endpoint tests
  - Agent ID generation tests  
  - Cluster listing tests
  - Input validation tests
  - Error handling tests

- **`test_integration.py`** - Integration tests for complete workflows
  - End-to-end onboarding flow
  - Multi-user scenarios
  - Cross-service interactions
  - Data consistency tests

- **`test_rate_limiting.py`** - Rate limiting functionality tests
  - Rate limiter unit tests
  - Endpoint rate limiting integration
  - Concurrent request handling
  - Rate limit configuration tests

- **`test_performance.py`** - Performance and load tests
  - Response time measurements
  - Concurrent operation tests
  - Memory usage monitoring
  - Scalability characteristics

### 🧪 Test Categories

#### Unit Tests
- Test individual functions and endpoints in isolation
- Mock external dependencies (database, RabbitMQ, authentication)
- Focus on business logic and edge cases

#### Integration Tests  
- Test complete workflows across multiple components
- Use real database (in-memory SQLite for tests)
- Test service interactions and data flow

#### Performance Tests
- Measure response times and throughput
- Test concurrent operations
- Monitor resource usage
- Validate scalability

#### Security Tests
- SQL injection prevention
- XSS attack mitigation  
- Input sanitization
- Rate limiting effectiveness

## 🚀 Running Tests

### Quick Start
```bash
# Make test runner executable
chmod +x run_tests.sh

# Run all tests
./run_tests.sh
```

### Manual Test Execution

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run specific test file
pytest tests/test_onboarding.py -v

# Run specific test
pytest tests/test_onboarding.py::TestOnboardCluster::test_successful_onboarding -v

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run only unit tests
pytest -m "unit" -v

# Run tests excluding slow ones
pytest -m "not slow" -v

# Run with maximum failures limit
pytest --maxfail=5

# Run in parallel (if pytest-xdist installed)
pytest -n auto
```

### 🏷️ Test Markers

Use markers to run specific categories of tests:

```bash
# Run only integration tests
pytest -m integration

# Run only performance tests  
pytest -m performance

# Run security-related tests
pytest -m security

# Exclude slow tests
pytest -m "not slow"
```

## 📊 Test Coverage

The test suite aims for high coverage across:

- **API Endpoints**: All REST endpoints tested
- **Business Logic**: Core onboarding workflows
- **Error Handling**: Exception scenarios and edge cases
- **Security**: Authentication, authorization, input validation
- **Performance**: Response times and concurrent operations

### Coverage Reports

After running tests with coverage:
- **Terminal**: Summary displayed in terminal
- **HTML**: Detailed report at `htmlcov/index.html`
- **Coverage Target**: Minimum 80% coverage required

## 🔧 Test Configuration

### Environment Setup
Tests use isolated environment with:
- In-memory SQLite database
- Mocked authentication
- Mocked RabbitMQ publishing
- Disabled rate limiting (for test speed)

### Fixtures (`conftest.py`)
- **`db_session`** - Fresh database for each test
- **`client`** - FastAPI test client
- **`mock_user`** - Mock authenticated user
- **`sample_agent`** - Pre-created agent in database
- **`sample_cluster`** - Pre-created cluster in database
- **`mock_rabbitmq`** - Mocked message queue operations

### Configuration (`pytest.ini`)
- Test discovery patterns
- Coverage settings
- Output formatting
- Asyncio support
- Warning filters

## 🐛 Debugging Tests

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure PYTHONPATH includes current directory
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Database Issues**
   ```bash
   # Tests use fresh in-memory DB, check fixture setup
   pytest tests/test_onboarding.py::test_name -v -s
   ```

3. **Async Test Issues**
   ```bash
   # Ensure pytest-asyncio is installed and configured
   pip install pytest-asyncio
   ```

### Debug Mode
```bash
# Run with debug output
pytest -v -s --tb=long

# Run single test with debugging
pytest tests/test_onboarding.py::TestOnboardCluster::test_successful_onboarding -v -s --pdb
```

## 📈 Performance Benchmarks

### Expected Performance Metrics
- **Onboarding Request**: < 2 seconds response time
- **List Clusters (50 items)**: < 1 second response time  
- **Agent ID Generation**: < 500ms response time
- **Concurrent Operations**: 10 parallel requests should complete < 5 seconds

### Load Testing
```bash
# Run performance tests
pytest tests/test_performance.py -v

# Run with performance profiling
pytest tests/test_performance.py --profile
```

## 🔒 Security Testing

### Security Test Coverage
- SQL injection prevention
- XSS attack mitigation
- Input validation and sanitization
- Authentication bypass attempts
- Rate limiting enforcement
- Data isolation between users

### Running Security Tests
```bash
# Run security-specific tests
pytest -m security -v

# Run tests with security focus
pytest tests/test_integration.py::TestSecurityValidation -v
```

## 🚀 CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: |
    cd backend/onboarding_service
    pip install -r requirements.txt
    pytest --cov=app --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./backend/onboarding_service/coverage.xml
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Run tests before commit
pre-commit install
```

## 📚 Writing New Tests

### Test Guidelines

1. **Follow Naming Conventions**
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test methods: `test_*`

2. **Use Descriptive Names**
   ```python
   def test_onboarding_with_invalid_agent_id_returns_404()
   def test_generate_agent_id_with_existing_cluster_association()
   ```

3. **Structure Tests with AAA Pattern**
   ```python
   def test_something():
       # Arrange
       setup_data = create_test_data()
       
       # Act  
       response = client.post("/endpoint", json=setup_data)
       
       # Assert
       assert response.status_code == 200
       assert response.json()["field"] == expected_value
   ```

4. **Use Appropriate Fixtures**
   ```python
   def test_with_database(db_session, sample_agent):
       # Test uses database and pre-created agent
   ```

5. **Mock External Dependencies**
   ```python
   @patch('app.routes.authenticate_request')
   def test_with_mocked_auth(mock_auth, client):
       mock_auth.return_value = {"id": 1, "username": "test"}
   ```

### Adding New Test Files

1. Create test file in `tests/` directory
2. Import necessary fixtures from `conftest.py`
3. Add appropriate markers for categorization
4. Update this README with new test descriptions

## 🤝 Contributing

When adding new features:

1. **Write Tests First** (TDD approach)
2. **Ensure High Coverage** (>80% for new code)
3. **Add Integration Tests** for new endpoints
4. **Update Performance Tests** if adding heavy operations
5. **Add Security Tests** for new input handling

### Test Review Checklist
- [ ] Tests cover happy path scenarios
- [ ] Tests cover error conditions
- [ ] Tests cover edge cases
- [ ] Mocks are appropriate and not over-mocked
- [ ] Performance implications considered
- [ ] Security implications tested
- [ ] Tests are fast and reliable
