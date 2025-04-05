import pandas as pd
import os
from waste_cutting_optimizer import WasteCuttingStockOptimizer

folder_path = r"C:\Users\FEDERICO\Documents\Python_Scripts\Projects\GitHub\Ottimizzazione taglio\examples"
file_name = 'My_profile.xlsx'
file_path = os.path.join(folder_path, file_name)

df = pd.read_excel(file_path, header=None, dtype=str)
    
def clean_number(value):
    """Converte un numero formattato con il punto come separatore delle migliaia in un intero."""
    try:
        # Se il valore è NaN o una stringa vuota, restituisci None
        if pd.isna(value) or value == '':
            return None
        # Converti in stringa, rimuovi il punto e trasforma in intero
        val = (str(value).replace('.', ''))
        return int(val)  # Rimuove solo i separatori di migliaia
    except (ValueError, AttributeError):
        return None  # Se non può essere convertito in int, restituisci None

def excel_to_raw_data(df):
    pieces = []
    num_cols = len(df.columns)

    for _, row in df.iterrows():
        if num_cols == 2:
            pieces.append((clean_number(row.iloc[1]), clean_number(row.iloc[0])))
        elif num_cols == 3:
            pieces.append((clean_number(row.iloc[2]), clean_number(row.iloc[1]), row.iloc[0]))  # Il terzo valore rimane invariato
        else:
            print('Errore: il file Excel non ha 2 o 3 colonne. Controlla i dati.')

    return pieces


longer_than = 4500
stock_length = 12000
blade_width = 2

pieces = excel_to_raw_data(df) 

#print('Pezzi da tagliare:', pieces)
cuts = WasteCuttingStockOptimizer(stock_length, blade_width, max_joints=1)

patterns, remaining = cuts.optimize_with_waste(pieces, longer_than)

cuts.print_solution(patterns, remaining)
cuts.print_summary(patterns, remaining)
order = 'Ord #1'
if '.' in file_name:
    last_dot_id = file_name.rfind(".")
    profile_name = file_name[:last_dot_id]
    bom_name = f"Distinta_{profile_name}.pdf"


cuts.generate_pdf(os.path.join(folder_path, bom_name), profilo=profile_name, commessa=order, num_columns=4)
