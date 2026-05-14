import unittest
import pandas as pd
from app.transform import transform_data

class TestTransform(unittest.TestCase):
    def test_transform_data_world_bank(self):
        input_df = pd.DataFrame([{
            'country': 'USA',
            'year': 2020,
            'gdp_per_capita': 60000,
            'source': 'World Bank'
        }])

        result = transform_data(input_df)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertListEqual(list(result.columns), ['country', 'year', 'gdp_per_capita', 'source'])

    def test_transform_data_missing_columns(self):
        input_df = pd.DataFrame([{'invalid': 'data'}])

        result = transform_data(input_df)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)

    def test_transform_data_empty(self):
        input_df = pd.DataFrame()

        result = transform_data(input_df)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)

if __name__ == '__main__':
    unittest.main()