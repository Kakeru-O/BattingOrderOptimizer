
import pandas as pd
import os

def add_speed_score(year: str, team: str, raw_dir="./data/raw"):
    """
    選手データに走力ポイントを追加する

    Args:
        year (str): 年度
        team (str): チーム名
        raw_dir (str): rawデータが格納されているディレクトリ

    Returns:
        pd.DataFrame: 走力ポイントを追加した選手データ
    """
    # data/rawから元データを読み込む
    raw_path = os.path.join(raw_dir, f"{year}_{team}.csv")
    try:
        df = pd.read_csv(raw_path)
    except FileNotFoundError:
        print(f"Error: {raw_path} not found.")
        return None

    # process_dataと同様にカラム名を英語に変換
    eng_columns = [
        'Player', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI',
        'SB', 'CS', 'SH', 'SF', 'BB', 'IBB', 'HBP', 'SO', 'GIDP', 'AVG', 'SLG', 'OBP'
    ]
    # 元のデータフレームのカラム数がeng_columnsと一致するか確認
    if len(df.columns) == len(eng_columns):
        df.columns = eng_columns
    else:
        # 選手名と成績データのみを抽出し、カラム名を再設定
        # 元データはヘッダーが2行あるため、2行目以降をデータとして扱う
        df = df.iloc[1:, :len(eng_columns)]
        df.columns = eng_columns


    # データ型を数値に変換（エラーは無視）
    for col in ['3B', 'SB', 'CS']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 走力ポイントを計算
    # 走力ポイント = (三塁打数 * 3) + (盗塁数 * 1) - (盗塁死数 * 2)
    df['Speed'] = (df['3B'] * 3) + (df['SB'] * 1) - (df['CS'] * 2)

    return df

def merge_and_save_processed_data(year: str, team: str, raw_dir="./data/raw", processed_dir="./data/processed"):
    """
    processedデータにSpeedスコアをマージして上書き保存する
    """
    # processedデータを読み込む
    processed_path = os.path.join(processed_dir, f"{year}_{team}.csv")
    try:
        df_processed = pd.read_csv(processed_path)
    except FileNotFoundError:
        print(f"Error: {processed_path} not found. Skipping.")
        return

    # 走力スコアデータを取得 (rawデータの場所を指定)
    df_speed = add_speed_score(year, team, raw_dir=raw_dir)
    if df_speed is None:
        return

    # 必要なカラムのみに絞る
    df_speed_simple = df_speed[['Player', 'Speed']]

    # processedデータとマージ
    df_merged = pd.merge(df_processed, df_speed_simple, on='Player', how='left')

    # SpeedスコアがNaNの場合は0で埋める
    df_merged['Speed'] = df_merged['Speed'].fillna(0)

    # 元のファイルを上書き保存
    df_merged.to_csv(processed_path, index=False)
    print(f"Successfully updated: {processed_path}")


def main(teams, year, raw_dir="./data/raw", processed_dir="./data/processed"):
    for team_id in teams:
        merge_and_save_processed_data(year, team_id, raw_dir=raw_dir, processed_dir=processed_dir)

if __name__ == "__main__":
    TEAMS = ["g", "t", "c", "db", "s", "d", "f", "e", "m", "l", "b", "h"]
    main(TEAMS, "2024")
