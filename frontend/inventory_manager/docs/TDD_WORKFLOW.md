# Test-Driven Development (TDD) Workflow

## Overview

This project follows **Test-Driven Development (TDD)** principles to ensure high code quality, maintainability, and confidence in refactoring.

## The Red-Green-Refactor Cycle

TDD follows a simple three-step cycle:

### 🔴 **RED** - Write a Failing Test

1. **Write a test first** before writing any production code
2. The test should **fail** because the feature doesn't exist yet
3. This ensures the test is actually testing something

```bash
# Write test in tests/test_feature.py
poetry run pytest tests/test_feature.py
# ❌ Test fails (expected)
```

### 🟢 **GREEN** - Make it Pass

1. Write the **minimum code** necessary to make the test pass
2. Don't worry about perfect code yet - just make it work
3. Run the test again to verify it passes

```bash
# Implement feature in src/
poetry run pytest tests/test_feature.py
# ✅ Test passes
```

### 🔵 **REFACTOR** - Improve the Code

1. **Clean up** the code while keeping tests green
2. Remove duplication, improve names, extract methods
3. Run tests frequently to ensure nothing breaks

```bash
# Refactor implementation
poetry run pytest tests/test_feature.py
# ✅ Tests still pass
```

## Example TDD Session

### Scenario: Implement Low Stock Detection

#### Step 1: RED - Write Failing Test

```python
# tests/test_inventory_service.py
def test_detect_low_stock_items():
    """Test identification of items below threshold."""
    from src.services.inventory_service import InventoryService
    
    service = InventoryService()
    
    inventory_df = pd.DataFrame([
        {'SKU': 'A', 'QtyOnHand': 2},   # Low
        {'SKU': 'B', 'QtyOnHand': 10},  # OK
    ])
    
    # Act
    low_stock = service.detect_low_stock(inventory_df, threshold=5)
    
    # Assert
    assert len(low_stock) == 1
    assert 'A' in low_stock['SKU'].values
```

**Run test:**
```bash
$ poetry run pytest tests/test_inventory_service.py::test_detect_low_stock_items -v

FAILED tests/test_inventory_service.py::test_detect_low_stock_items
ImportError: cannot import name 'InventoryService' from 'src.services'
```

✅ **Good!** Test fails as expected.

#### Step 2: GREEN - Minimal Implementation

```python
# src/services/inventory_service.py
import pandas as pd

class InventoryService:
    def detect_low_stock(self, inventory_df: pd.DataFrame, threshold: int = 5) -> pd.DataFrame:
        """Detect items below stock threshold."""
        return inventory_df[inventory_df['QtyOnHand'] <= threshold]
```

**Run test again:**
```bash
$ poetry run pytest tests/test_inventory_service.py::test_detect_low_stock_items -v

PASSED tests/test_inventory_service.py::test_detect_low_stock_items ✓
```

✅ **Success!** Test passes with minimal code.

#### Step 3: REFACTOR - Improve

```python
# src/services/inventory_service.py
import pandas as pd
from typing import Optional

class InventoryService:
    def detect_low_stock(
        self, 
        inventory_df: pd.DataFrame, 
        threshold: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Detect items below stock threshold.
        
        Args:
            inventory_df: Inventory data with QtyOnHand column
            threshold: Stock level threshold (default: from config)
            
        Returns:
            DataFrame of low stock items
        """
        if threshold is None:
            threshold = self._get_default_threshold()
        
        low_stock = inventory_df[inventory_df['QtyOnHand'] <= threshold].copy()
        low_stock = self._add_priority_levels(low_stock, threshold)
        
        return low_stock
```

**Run test:**
```bash
$ poetry run pytest tests/test_inventory_service.py::test_detect_low_stock_items -v

PASSED tests/test_inventory_service.py::test_detect_low_stock_items ✓
```

✅ **Still passes!** Safe to refactor.

## TDD Best Practices

### 1. **Write Tests First, Always**
   - Resist the urge to write code before tests
   - Tests define the specification

### 2. **One Test at a Time**
   - Focus on one failing test
   - Don't write multiple failing tests

### 3. **Small Steps**
   - Write simple tests first
   - Gradually increase complexity

### 4. **Test Behavior, Not Implementation**
   ```python
   # ❌ Bad - tests implementation details
   def test_uses_pandas_groupby():
       assert service._uses_groupby == True
   
   # ✅ Good - tests behavior
   def test_aggregates_sales_by_sku():
       result = service.aggregate_sales(sales_df)
       assert result['total_quantity'] == expected
   ```

### 5. **Keep Tests Fast**
   - Use mocks for external dependencies
   - No database or API calls in unit tests
   - Fast tests = run frequently

### 6. **Meaningful Test Names**
   ```python
   # ❌ Bad
   def test_1():
       ...
   
   # ✅ Good
   def test_apply_sales_reduces_quantity_on_hand():
       ...
   ```

## Running Tests

### Run All Tests
```bash
poetry run pytest
```

### Run Specific Test File
```bash
poetry run pytest tests/test_inventory_service.py
```

### Run Specific Test
```bash
poetry run pytest tests/test_inventory_service.py::test_detect_low_stock
```

### Run with Coverage
```bash
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Run in Watch Mode
```bash
poetry run pytest-watch
```

## Coverage Requirements

- **Minimum coverage**: 80%
- **Target coverage**: 90%+
- **Critical paths**: 100% coverage (auth, payments, data integrity)

```bash
# Check coverage
poetry run pytest --cov=src --cov-report=term-missing

# Fail if below threshold
poetry run pytest --cov=src --cov-fail-under=80
```

## Test Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── test_lightspeed_client.py      # Gateway/Adapter tests
├── test_inventory_service.py      # Business logic tests
├── test_sheets_repo.py            # Repository tests
├── integration/
│   ├── test_sync_workflow.py      # End-to-end tests
│   └── test_api_integration.py    # API integration tests
└── fixtures/
    ├── sample_products.json        # Test data
    └── sample_sales.csv            # Test data
```

## Common TDD Patterns

### 1. **Arrange-Act-Assert (AAA)**
```python
def test_example():
    # Arrange - set up test data
    service = InventoryService()
    data = create_test_data()
    
    # Act - execute the behavior
    result = service.process(data)
    
    # Assert - verify the outcome
    assert result == expected
```

### 2. **Given-When-Then (BDD Style)**
```python
def test_example():
    # Given - preconditions
    given_inventory_has_low_stock()
    
    # When - action
    when_sync_runs()
    
    # Then - outcome
    then_restock_list_is_updated()
```

### 3. **Test Fixtures**
```python
@pytest.fixture
def sample_inventory():
    """Reusable test data."""
    return pd.DataFrame([...])

def test_with_fixture(sample_inventory):
    result = process(sample_inventory)
    assert result is not None
```

## Debugging Failing Tests

### 1. **Use pytest -v for verbose output**
```bash
poetry run pytest -v
```

### 2. **Use --pdb to drop into debugger**
```bash
poetry run pytest --pdb
```

### 3. **Use print statements (pytest captures output)**
```bash
poetry run pytest -s  # Show print statements
```

### 4. **Run only failed tests**
```bash
poetry run pytest --lf  # Last failed
poetry run pytest --ff  # Failed first
```

## CI/CD Integration

Tests run automatically on:
- **Every push** to any branch
- **Every pull request**
- **Before merge** to main

```yaml
# .github/workflows/tdd.yml
- name: Run tests
  run: poetry run pytest --cov=src --cov-fail-under=80
```

## Mocking External Dependencies

### Mock Lightspeed API
```python
@patch('src.infra.lightspeed_client.requests.Session.get')
def test_api_call(mock_get):
    mock_get.return_value.json.return_value = {'data': []}
    # Test code here
```

### Mock Google Sheets
```python
@patch('gspread.authorize')
def test_sheets_read(mock_authorize):
    mock_client = Mock()
    mock_authorize.return_value = mock_client
    # Test code here
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [TDD by Example (Kent Beck)](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
- [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)

---

**Remember**: Red → Green → Refactor. Repeat. 🔴 🟢 🔵
