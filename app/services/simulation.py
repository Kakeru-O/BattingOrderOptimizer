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

def _should_advance_extra_base_single(runner_speed, current_outs):
    """
    ランナーが追加の塁に進むべきかを判定するヘルパー関数。
    """
    if runner_speed == 0: # No runner
        return False
    prob = 0.3
    if runner_speed > 5: # Speed score
        prob += 0.3
    if current_outs == 2:
        prob += 0.2
    return np.random.rand() < prob

def _advance_runners_numpy(runners_speed, hit_type, batter_speed, outs):
    """
    NumPyベースでランナーの進塁を処理するヘルパー関数。
    runners_speed: np.array([speed_1b, speed_2b, speed_3b]) (0 if no runner)
    hit_type: '1B', '2B', '3B', '3B', 'HR', 'BB+HBP'
    batter_speed: 打者のSpeedスコア
    outs: 現在のアウトカウント
    """
    runs_scored = 0
    # Create a temporary array to hold the state of bases (0: Home, 1: 1st, 2: 2nd, 3: 3rd)
    # Value is speed of runner, 0 if empty
    bases = np.zeros(4, dtype=int)
    if runners_speed[0] > 0: bases[1] = runners_speed[0] # 1st base
    if runners_speed[1] > 0: bases[2] = runners_speed[1] # 2nd base
    if runners_speed[2] > 0: bases[3] = runners_speed[2] # 3rd base

    if hit_type == 'BB+HBP':
        # Forced advancements
        if bases[1] > 0: # Runner on 1st
            if bases[2] > 0: # Runner on 2nd
                if bases[3] > 0: # Runner on 3rd (bases loaded)
                    runs_scored += 1 # 3rd scores
                    bases[3] = bases[2] # 2nd to 3rd
                    bases[2] = bases[1] # 1st to 2nd
                    bases[1] = batter_speed # Batter to 1st
                else: # 1st and 2nd occupied
                    bases[3] = bases[2] # 2nd to 3rd
                    bases[2] = bases[1] # 1st to 2nd
                    bases[1] = batter_speed # Batter to 1st
            else: # Only 1st occupied
                bases[2] = bases[1] # 1st to 2nd
                bases[1] = batter_speed # Batter to 1st
        else: # Bases empty or only 2nd/3rd occupied
            bases[1] = batter_speed # Batter to 1st

    elif hit_type == '1B':
        # 3rd base runner
        if bases[3] > 0:
            runs_scored += 1
            bases[3] = 0
        # 2nd base runner
        if bases[2] > 0:
            if _should_advance_extra_base_single(bases[2], outs):
                runs_scored += 1
            else:
                bases[3] = bases[2]
            bases[2] = 0
        # 1st base runner
        if bases[1] > 0:
            # Check if 2nd base is now occupied by previous runner
            can_try_for_third = (bases[2] == 0) # If 2nd base is empty after 2nd base runner moved
            if can_try_for_third and _should_advance_extra_base_single(bases[1], outs):
                bases[3] = bases[1]
            else:
                bases[2] = bases[1]
            bases[1] = 0
        # Batter to 1st
        bases[1] = batter_speed

    elif hit_type == '2B':
        # 3rd, 2nd base runners score
        if bases[3] > 0: runs_scored += 1
        if bases[2] > 0: runs_scored += 1
        bases[3] = 0
        bases[2] = 0
        # 1st base runner
        if bases[1] > 0:
            if _should_advance_extra_base_single(bases[1], outs):
                runs_scored += 1
            else:
                bases[3] = bases[1]
            bases[1] = 0
        # Batter to 2nd
        bases[2] = batter_speed

    elif hit_type == '3B':
        # All runners score
        for i in range(1, 4):
            if bases[i] > 0:
                runs_scored += 1
                bases[i] = 0
        # Batter to 3rd
        bases[3] = batter_speed

    elif hit_type == 'HR':
        # All runners score + batter scores
        for i in range(1, 4):
            if bases[i] > 0:
                runs_scored += 1
                bases[i] = 0
        runs_scored += 1 # Batter scores

    new_runners_speed = np.array([bases[1], bases[2], bases[3]])
    return runs_scored, new_runners_speed

def simulate_inning(batting_order, current_batter_abs_index, game_log, enable_log=True):
    """
    1イニングのシミュレーションを行う

    Args:
        batting_order (pd.DataFrame): 打順データ (Speedスコアを含む)
        current_batter_abs_index (int): このイニングの先頭打者の通算打席インデックス
        game_log (dict): 試合全体の成績を記録する辞書 (キーは打順ポジション)

    Returns:
        tuple: (このイニングの得点, 次のイニングの先頭打者の通算打席インデックス, このイニングのイベントログ)
    """
    outs = 0
    runners_speed = np.zeros(3, dtype=int)  # 1塁, 2塁, 3塁のランナーのSpeedスコア (0 if no runner)
    runs = 0
    batter_abs_index = current_batter_abs_index
    inning_events = {} if enable_log else None

    while outs < 3:
        batter_pos = batter_abs_index % 9
        player_stats = batting_order.iloc[batter_pos]
        result = simulate_at_bat(player_stats)

        game_log[batter_pos][result] += 1
        rbi = 0

        if result == 'Out':
            outs += 1
        else:
            runs_this_play, new_runners_speed = _advance_runners_numpy(
                runners_speed, result, player_stats['Speed'], outs
            )
            runs += runs_this_play
            rbi += runs_this_play # For simplicity, RBI is equal to runs scored on the play
            runners_speed = new_runners_speed

        if enable_log:
            log_event = result
            if rbi > 0:
                log_event += f" (+{rbi})"
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
        runs, next_batter_abs_index, inning_events = simulate_inning(batting_order, batter_abs_index, game_log, enable_log=enable_inning_log)
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

    # Define the order of keys for consistent indexing
    result_keys = ['1B', '2B', '3B', 'HR', 'BB+HBP', 'Out', 'RBI']

    for i in range(num_trials):
        # 打順をシャッフル
        batting_order = selected_players_df.sample(frac=1).reset_index(drop=True)

        total_runs_for_trial = 0
        # 1シーズン(143試合)の成績を合計するためのログをNumPy配列で初期化
        season_game_log_array = np.zeros((9, len(result_keys)), dtype=int)

        for _ in range(143):
            # 高速化のためイニングログは無効にする
            result = simulate_game(batting_order, enable_inning_log=False)
            total_runs_for_trial += result['total_runs']

            # Convert current game_log to NumPy array and add to season_game_log_array
            current_game_log_array = np.zeros((9, len(result_keys)), dtype=int)
            for p in range(9):
                for k_idx, key in enumerate(result_keys):
                    current_game_log_array[p, k_idx] = result['game_log'][p][key]
            season_game_log_array += current_game_log_array
        
        avg_runs = total_runs_for_trial / 143

        # Convert season_game_log_array back to dictionary for output
        season_game_log_dict = {}
        for p in range(9):
            season_game_log_dict[p] = {key: season_game_log_array[p, k_idx] for k_idx, key in enumerate(result_keys)}

        if avg_runs > best_order_info["avg_runs"]:
            best_order_info = {
                "order_df": batting_order,
                "avg_runs": avg_runs,
                "total_runs": total_runs_for_trial,
                "stats": season_game_log_dict # Use the converted dictionary
            }
        
        if avg_runs < worst_order_info["avg_runs"]:
            worst_order_info = {
                "order_df": batting_order,
                "avg_runs": avg_runs,
                "total_runs": total_runs_for_trial,
                "stats": season_game_log_dict # Use the converted dictionary
            }

        progress_bar.progress((i + 1) / num_trials)

    return {
        "best_order": best_order_info,
        "worst_order": worst_order_info
    }