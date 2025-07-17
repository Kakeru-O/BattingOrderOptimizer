import sys
import os

# プロジェクトのルートディレクトリをPythonのパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from app.services.simulation import simulate_game, estimate_best_batting_order

# テスト用のダミーデータを作成
data = {
    'Player': ['FastA', 'SlowB', 'FastC', 'SlowD', 'FastE', 'SlowF', 'FastG', 'FastH', 'SlowI'],
    '1B_ratio': [0.2, 0.15, 0.18, 0.15, 0.14, 0.18, 0.19, 0.13, 0.12],
    '2B_ratio': [0.05, 0.04, 0.06, 0.05, 0.07, 0.04, 0.03, 0.08, 0.05],
    '3B_ratio': [0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.02, 0.01],
    'HR_ratio': [0.03, 0.05, 0.03, 0.06, 0.02, 0.01, 0.04, 0.05, 0.06],
    'BB+HBP_ratio': [0.1, 0.08, 0.12, 0.09, 0.11, 0.07, 0.1, 0.08, 0.11],
    # Out_ratioは残り
    'Speed': [10, 1, 12, 2, 15, 3, 8, 9, 0] # Fast選手はSpeed > 5
}
df = pd.DataFrame(data)
df['Out_ratio'] = 1 - df[['1B_ratio', '2B_ratio', '3B_ratio', 'HR_ratio', 'BB+HBP_ratio']].sum(axis=1)

def test_single_game_simulation():
    print("--- Running Single Game Simulation Test ---")
    game_result = simulate_game(df, enable_inning_log=True)
    
    assert isinstance(game_result['total_runs'], int)
    assert isinstance(game_result['game_log'], dict)
    print(f"Total Runs: {game_result['total_runs']}")

    # イニングログの表示
    inning_log_df = pd.DataFrame(game_result['inning_log'])
    inning_log_df.index = df['Player']
    inning_log_df.columns = [f'{i+1}回' for i in range(9)]
    print("--- Inning Log ---")
    print(inning_log_df)
    print("Single Game Simulation Test Passed!")

def test_estimate_best_batting_order():
    print("\n--- Estimating Best Batting Order Test (10 trials) ---")
    class DummyProgressBar:
        def progress(self, value):
            pass

    result = estimate_best_batting_order(df, 10, DummyProgressBar())
    
    assert 'best_order' in result
    assert 'worst_order' in result
    assert result['best_order']['avg_runs'] >= result['worst_order']['avg_runs']
    
    print("Best Order:")
    print(result['best_order']['order_df']['Player'].tolist())
    print(f"Average Runs: {result['best_order']['avg_runs']:.2f}")
    print("--- vs ---")
    print("Worst Order:")
    print(result['worst_order']['order_df']['Player'].tolist())
    print(f"Average Runs: {result['worst_order']['avg_runs']:.2f}")
    print("Estimate Best Batting Order Test Passed!")

if __name__ == "__main__":
    test_single_game_simulation()
    test_estimate_best_batting_order()
