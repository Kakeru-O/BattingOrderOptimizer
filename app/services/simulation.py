import numpy as np
import pandas as pd

def simulate_at_bat(player_stats):
    """
    1打席の結果をシミュレートする

    Args:
        player_stats (pd.Series): 選手の成績データ

    Returns:
        str: 打席結果 (e.g., '1B', '2B', 'HR', 'BB+HBP', 'Out')
    """
    probabilities = player_stats[['1B_ratio', '2B_ratio', '3B_ratio', 'HR_ratio', 'BB+HBP_ratio', 'Out_ratio']].values.astype('float64')
    # 確率の合計が1になるように正規化（浮動小数点誤差を考慮）
    probabilities /= probabilities.sum()

    result = np.random.choice(
        ['1B', '2B', '3B', 'HR', 'BB+HBP', 'Out'],
        p=probabilities
    )
    return result

def simulate_inning(batting_order, current_batter_abs_index, game_log):
    """
    1イニングのシミュレーションを行う

    Args:
        batting_order (pd.DataFrame): 打順データ (0-8のインデックスを持つ)
        current_batter_abs_index (int): このイニングの先頭打者の通算打席インデックス
        game_log (dict): 試合全体の成績を記録する辞書 (キーは打順ポジション)

    Returns:
        tuple: (このイニングの得点, 次のイニングの先頭打者の通算打席インデックス, このイニングのイベントログ)
    """
    outs = 0
    runners = [0, 0, 0]  # 1塁, 2塁, 3塁
    runs = 0
    batter_abs_index = current_batter_abs_index
    inning_events = {}

    while outs < 3:
        batter_pos = batter_abs_index % 9
        player_stats = batting_order.iloc[batter_pos]
        result = simulate_at_bat(player_stats)

        # 試合全体の成績を更新
        game_log[batter_pos][result] += 1

        rbi = 0
        # 打席結果に応じたランナーの進塁と得点計算
        if result == 'Out':
            outs += 1
        elif result == 'BB+HBP':
            # 四死球: 満塁なら押し出しで1点、そうでなければランナーを進める
            if runners[0] == 1 and runners[1] == 1 and runners[2] == 1:
                rbi = 1
                runs += 1
            elif runners[0] == 1 and runners[1] == 1:
                runners[2] = 1 # 2塁ランナーが3塁へ
            elif runners[0] == 1:
                runners[1] = 1 # 1塁ランナーが2塁へ
            runners[0] = 1 # 打者が1塁へ
        elif result == '1B':
            # シングルヒット: 3塁ランナーは必ず生還、2塁ランナーは3塁へ、1塁ランナーは2塁へ
            rbi = runners[2]
            runs += runners[2]
            runners[2] = runners[1]
            runners[1] = runners[0]
            runners[0] = 1
        elif result == '2B':
            # ダブルヒット: 2,3塁ランナーは生還、1塁ランナーは3塁へ
            rbi = runners[2] + runners[1]
            runs += rbi
            runners[2] = runners[0]
            runners[1] = 1
            runners[0] = 0
        elif result == '3B':
            # トリプルヒット: 全てのランナーが生還
            rbi = sum(runners)
            runs += rbi
            runners = [0, 0, 1]
        elif result == 'HR':
            # ホームラン: 全てのランナーと打者が生還
            rbi = sum(runners) + 1
            runs += rbi
            runners = [0, 0, 0]

        # イベントログ用の文字列を作成
        log_event = result
        if rbi > 0:
            log_event += f" (+{rbi})"

        # イニングごとのログを更新
        if batter_pos not in inning_events:
            inning_events[batter_pos] = log_event
        else:
            inning_events[batter_pos] += f", {log_event}"
        
        if rbi > 0:
            game_log[batter_pos]['RBI'] += rbi

        batter_abs_index += 1

    return runs, batter_abs_index, inning_events

def simulate_game(batting_order, enable_inning_log=True):
    """
    1試合（9イニング）のシミュレーションを行う

    Args:
        batting_order (pd.DataFrame): 打順データ (0-8のインデックスを持つ)
        enable_inning_log (bool): Trueの場合、イニングごとの詳細ログを生成する

    Returns:
        dict: 試合結果
    """
    total_runs = 0
    batter_abs_index = 0
    game_log = {i: {'1B': 0, '2B': 0, '3B': 0, 'HR': 0, 'BB+HBP': 0, 'Out': 0, 'RBI': 0} for i in range(9)}
    inning_by_inning_log = {i: [''] * 9 for i in range(9)} if enable_inning_log else None

    for inning in range(9):
        runs, next_batter_abs_index, inning_events = simulate_inning(batting_order, batter_abs_index, game_log)
        total_runs += runs
        batter_abs_index = next_batter_abs_index
        if enable_inning_log:
            for batter_pos, event in inning_events.items():
                inning_by_inning_log[batter_pos][inning] = event

    return {"total_runs": total_runs, "game_log": game_log, "inning_log": inning_by_inning_log}

def estimate_best_batting_order(selected_players_df, num_trials, progress_bar):
    """
    最良打順を推定するために、複数回のシミュレーションを実行する

    Args:
        selected_players_df (pd.DataFrame): 選択された9人の選手データ
        num_trials (int): 試行回数
        progress_bar: Streamlitのプログレスバーオブジェクト

    Returns:
        dict: 最良打順、最悪打順、それぞれの平均得点と成績
    """
    best_order_info = {"avg_runs": 0}
    worst_order_info = {"avg_runs": float('inf')}

    for i in range(num_trials):
        # 打順をシャッフル
        batting_order = selected_players_df.sample(frac=1).reset_index(drop=True)

        total_runs_for_trial = 0
        # 1シーズン(143試合)の成績を合計するためのログ
        season_game_log = {p: {'1B': 0, '2B': 0, '3B': 0, 'HR': 0, 'BB+HBP': 0, 'Out': 0, 'RBI': 0} for p in range(9)}

        for _ in range(143):
            # 高速化のためイニングログは無効にする
            result = simulate_game(batting_order, enable_inning_log=False)
            total_runs_for_trial += result['total_runs']
            for p in range(9):
                for key in season_game_log[p]:
                    season_game_log[p][key] += result['game_log'][p][key]
        
        avg_runs = total_runs_for_trial / 143

        if avg_runs > best_order_info["avg_runs"]:
            best_order_info = {
                "order_df": batting_order,
                "avg_runs": avg_runs,
                "total_runs": total_runs_for_trial,
                "stats": season_game_log
            }
        
        if avg_runs < worst_order_info["avg_runs"]:
            worst_order_info = {
                "order_df": batting_order,
                "avg_runs": avg_runs,
                "total_runs": total_runs_for_trial,
                "stats": season_game_log
            }

        progress_bar.progress((i + 1) / num_trials)

    return {
        "best_order": best_order_info,
        "worst_order": worst_order_info
    }