import pandas as pd
import numpy as np

def get_default_lineup(year: str, league: str, team_abbr: str):
    """
    指定された年度、リーグ、チームのデフォルトスタメン（各ポジション最多先発出場選手）を抽出する。

    Args:
        year (str): 年度 (例: "2024")
        league (str): リーグ ("Pacific" または "Central")
        team_abbr (str): チーム略称 (例: "M" for Marines)

    Returns:
        dict: ポジション名をキー、選手名を値とする辞書。投手は含まない。
              例: {'捕': '選手A', '一': '選手B', ...}
    """
    url = f'https://nf3.sakura.ne.jp/{year}/{league}/{team_abbr}/t/kiyou.htm'
    try:
        # header=[0, 1] で2行をヘッダーとして読み込む
        tables = pd.read_html(url, header=[0, 1])
        df = tables[1] # 2番目のテーブルが起用情報
    except Exception as e:
        print(f"Error reading HTML from {url}: {e}")
        return {}

    # カラム名の整形
    # MultiIndexのカラム名を結合して扱いやすくする
    # 例: ('捕手', '先発') -> '捕手_先発'
    # ただし、('名前', '名前') のような場合は '名前' にする
    new_columns = []
    for col in df.columns.values:
        if isinstance(col, tuple):
            if col[0] == col[1]: # 例: ('名前', '名前')
                new_columns.append(col[0])
            else:
                new_columns.append('_'.join(col).strip())
        else:
            new_columns.append(col)
    df.columns = new_columns

    # デバッグプリントを削除
    # print("--- DataFrame Columns after processing ---")
    # print(df.columns)

    # 不要なカラムを削除 (背番、守備、試合、途中、変更)
    # 選手名カラムは '名前'
    cols_to_drop = [col for col in df.columns if 
                    col.startswith('背番') or 
                    col.startswith('守備') or 
                    col.startswith('試合') or 
                    col.endswith('_途中') or 
                    col.endswith('_変更')]
    df = df.drop(columns=cols_to_drop)

    # 選手名から<a>タグを除去
    df['名前'] = df['名前'].apply(lambda x: x.split('>')[1].split('<')[0] if '<a' in str(x) else x)

    default_lineup = {}
    selected_players = set()

    # ポジションの優先順位 (一般的な野球のポジション)
    # 投手(P)は含めない
    # DHはパ・リーグのみ
    position_map = {
        '捕手': '捕',
        '一塁': '一',
        '二塁': '二',
        '三塁': '三',
        '遊撃': '遊',
        '左翼': '左',
        '中堅': '中',
        '右翼': '右',
        'ＤＨ': '指'
    }
    # 守備位置の表示順
    display_order = ['捕', '一', '二', '三', '遊', '左', '中', '右', '指']

    # 各ポジションの最多先発出場選手を抽出
    for pos_jp, pos_abbr in position_map.items():
        start_col = f'{pos_jp}_先発'
        if start_col not in df.columns:
            continue

        # ポジションごとの選手と先発出場数を抽出
        # '-' を 0 に変換し、数値型にする
        df_pos_players = df[['名前', start_col]].copy()
        df_pos_players[start_col] = pd.to_numeric(df_pos_players[start_col].replace('-', 0), errors='coerce').fillna(0).astype(int)
        
        # 先発出場数でソート
        df_pos_players = df_pos_players.sort_values(by=start_col, ascending=False)

        # 最多出場選手を抽出 (重複を避ける)
        for idx, row in df_pos_players.iterrows():
            player_name = row['名前']
            games_started = row[start_col]

            if games_started == 0: # 先発出場がない場合はスキップ
                continue

            if player_name not in selected_players:
                default_lineup[pos_abbr] = player_name
                selected_players.add(player_name)
                break # このポジションの選手が見つかったので次へ
    
    # セ・リーグの場合、DH(指)を除外
    if league == "Central" and '指' in default_lineup:
        del default_lineup['指']

    # 結果をdisplay_orderに基づいてソート
    sorted_lineup = {pos: default_lineup[pos] for pos in display_order if pos in default_lineup}

    return sorted_lineup


if __name__ == "__main__":
    year=2024
    league="Pacific"
    team="M"
    print(get_default_lineup(year,league,team))
    