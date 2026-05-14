import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from app.load import load_data

class TestLoad(unittest.TestCase):
    @patch('app.load.create_engine')
    @patch('app.load.Path') # To bypass schema file checks during testing
    @patch('pandas.DataFrame.to_sql')
    def test_load_data_success(self, mock_to_sql, mock_path, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_path.return_value.exists.return_value = False # Skip schema execution in unit test

        input_df = pd.DataFrame([{
            'country': 'USA',
            'year': 2020,
            'gdp_per_capita': 60000,
            'source': 'World Bank'
        }])

        load_data(input_df)
        
        # Verify it uses the updated table name
        mock_to_sql.assert_called_once()
        args, kwargs = mock_to_sql.call_args
        self.assertEqual(args[0], 'gdp_per_capita_data')
        self.assertEqual(kwargs['if_exists'], 'replace')

    def test_load_data_empty(self):
        # Testing the early return logic
        load_data(pd.DataFrame())
        # Success if no exceptions raised

if __name__ == '__main__':
    unittest.main()