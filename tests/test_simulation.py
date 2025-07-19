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
    'SO_ratio': [0.1, 0.2, 0.15, 0.2, 0.1, 0.15, 0.2, 0.15, 0.2],
    'Ground_Out_ratio': [0.3, 0.2, 0.2, 0.2, 0.3, 0.2, 0.2, 0.2, 0.2],
    'Fly_Out_ratio': [0.2, 0.27, 0.25, 0.24, 0.25, 0.24, 0.23, 0.24, 0.25],
    'Out_ratio': [0.6, 0.67, 0.6, 0.64, 0.65, 0.59, 0.63, 0.59, 0.65], # SO+GO+FO
    'Speed': [10, 1, 12, 2, 15, 3, 8, 9, 0] # Fast選手はSpeed > 5
}
df = pd.DataFrame(data)
# 確率の合計が1になるように正規化
prob_cols = ['1B_ratio', '2B_ratio', '3B_ratio', 'HR_ratio', 'BB+HBP_ratio', 'SO_ratio', 'Ground_Out_ratio', 'Fly_Out_ratio']
df[prob_cols] = df[prob_cols].div(df[prob_cols].sum(axis=1), axis=0)

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

def test_new_events_simulation():
    """犠打や進塁打が正しく機能するかをテストする"""
    print("\n--- Running New Events Simulation Test ---")
    # アウトになりやすい選手と、なりにくい選手を作成
    data = {
        'Player': ['BuntMan', 'HitterMan'],
        '1B_ratio': [0.1, 0.3],
        '2B_ratio': [0.01, 0.1],
        '3B_ratio': [0.0, 0.01],
        'HR_ratio': [0.0, 0.05],
        'BB+HBP_ratio': [0.1, 0.1],
        'SO_ratio': [0.1, 0.1],
        'Ground_Out_ratio': [0.4, 0.12],
        'Fly_Out_ratio': [0.29, 0.12],
        'Out_ratio': [0.79, 0.34], # BuntManはアウトになりやすい
        'Speed': [5, 5]
    }
    test_df = pd.DataFrame(data)
    # 9人に増やす
    full_order = pd.concat([test_df] * 5, ignore_index=True).head(9)

    # 100試合シミュレーションして、BuntManの犠打試行が多いことを確認
    game_logs = [simulate_game(full_order, enable_inning_log=False)['game_log'] for _ in range(100)]
    
    buntman_sac_attempts = sum(log[0]['Sacrifice_Attempts'] for log in game_logs)
    hitterman_sac_attempts = sum(log[1]['Sacrifice_Attempts'] for log in game_logs)

    print(f"BuntMan Sacrifice Attempts: {buntman_sac_attempts}")
    print(f"HitterMan Sacrifice Attempts: {hitterman_sac_attempts}")

    assert buntman_sac_attempts > hitterman_sac_attempts
    print("New Events Simulation Test Passed!")


if __name__ == "__main__":
    test_single_game_simulation()
    test_estimate_best_batting_order()
    test_new_events_simulation()
