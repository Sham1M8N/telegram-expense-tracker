import unittest
import sqlite3
import os
from main import save_expense_to_db # Import your function

class TestExpenseTracker(unittest.TestCase):
    
    def setUp(self):
        """Runs before every test. Sets up a clean environment."""
        self.test_db = "test_expenses.db"

    def tearDown(self):
        """Runs after every test. Cleans up the file."""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_save_expense(self):
        """Test if saving an expense actually writes to the DB."""
        print("Testing: Save Expense...")
        
        # 1. Execute the function
        user_id = 12345
        amount = 50.00
        category = "TestFood"
        
        save_expense_to_db(user_id, amount, category, self.test_db)

        # 2. Verify (Assert) the result manually
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT amount, category FROM expenses WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()

        # 3. The Moment of Truth
        self.assertIsNotNone(row, "The row should exist in the DB")
        self.assertEqual(row[0], 50.00, "Amount should be 50.00")
        self.assertEqual(row[1], "TestFood", "Category should be TestFood")
        
        print("✅ Save Expense Test Passed!")

if __name__ == '__main__':
    unittest.main()