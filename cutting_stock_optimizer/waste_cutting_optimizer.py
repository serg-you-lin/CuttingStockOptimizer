from typing import List, Tuple, Dict, Union, Optional
from dataclasses import dataclass
from collections import Counter, defaultdict
from itertools import combinations
from cutting_stock_optimizer import StrictCuttingStockOptimizer, CuttingPattern, MarkedPiece
from PDF_cut_list import CuttingListPDF

@dataclass
class JointCombination:
    bar_indices: List[int]
    wastes: List[float]
    total_waste: float

class WasteCuttingStockOptimizer(StrictCuttingStockOptimizer):
    def __init__(self, stock_length: float, blade_width: float, min_waste: float = 100, max_joints: int = 1, excluded_to_joint: Union[List[int], Tuple, int] = None):
        super().__init__(stock_length, blade_width)
        self._cuts_dict = {}
        self.max_waste_index = None
        self.max_waste_bar = None
        self.min_waste = min_waste
        self.max_joints = max_joints
        
        # Normalizza excluded_to_joint a una lista di indici
        if excluded_to_joint is None:
            self.excluded_to_joint = []
        elif isinstance(excluded_to_joint, (list, tuple)):
            if all(isinstance(x, int) for x in excluded_to_joint):
                # È già una lista di indici
                self.excluded_to_joint = list(excluded_to_joint)
            elif len(excluded_to_joint) >= 2 and isinstance(excluded_to_joint[0], (int, float)):
                # È un singolo pezzo
                self._temp_excluded_piece = excluded_to_joint
                self.excluded_to_joint = []
            else:
                raise ValueError("excluded_to_joint deve essere una lista di indici o un singolo pezzo")
        elif isinstance(excluded_to_joint, int):
            self.excluded_to_joint = [excluded_to_joint]
        else:
            raise ValueError("excluded_to_joint deve essere una lista di indici, un indice singolo, o un pezzo da escludere")
        #print("\nDEBUG: Inizializzazione joint_combinations come defaultdict(int)")
        self.joint_combinations = defaultdict(int)
        self._original_pieces = None
        self.iteration = 0
        self.total_waste = 0
        self.piece_counts = Counter()
        self.patterns = None
        self.remaining = None

    
    def _get_piece_length(self, piece):
        return piece.length if isinstance(piece, MarkedPiece) else piece
    
    def _get_piece_mark(self, piece):
        return piece.mark if isinstance(piece, MarkedPiece) else None

    def _generate_cuts_dict(self, patterns):
        self._cuts_dict = {
            i: (pattern.cuts, pattern.waste) 
            for i, pattern in enumerate(patterns)
        }

    def _find_max_waste_bar(self):
        if not self._cuts_dict:
            return None, None
        
        available_bars = {k: v for k, v in self._cuts_dict.items() 
                        if v[1] >= self.min_waste}
        
        if not available_bars:
            return None, None
            
        max_index = max(available_bars.keys(), 
                       key=lambda k: (available_bars[k][1], k))
        return max_index, available_bars[max_index]

    def _find_waste_combinations_n(self, target_length: float, n_joints: int) -> List[JointCombination]:
        print(f"\nCercando combinazioni per {n_joints} giunzioni:")
        print(f"Target length: {target_length:.2f}")
        
        combinations_list = []
        for bar_indices in combinations(self._cuts_dict.keys(), n_joints):
            if self.max_waste_index in bar_indices:
                continue
                
            wastes = [self._cuts_dict[i][1] for i in bar_indices]
            if all(waste >= self.min_waste for waste in wastes):
                total_waste = sum(wastes) - (n_joints - 1) * self.blade_width
                if total_waste >= target_length:
                    combination = JointCombination(
                        list(bar_indices),
                        wastes,
                        total_waste
                    )
                    combinations_list.append(combination)
                    print(f"Trovata combinazione valida:")
                    print(f"  Barre: {combination.bar_indices}")
                    print(f"  Scarti: {[f'{w:.2f}' for w in combination.wastes]}")
                    print(f"  Scarto totale: {combination.total_waste:.2f}")

        combinations_list.sort(key=lambda x: abs(x.total_waste - target_length))
        return combinations_list

    def _process_oversize_pieces(self, pieces):
        processed = []
        processed_count = 0  # Contatore per generare marche fittizie uniche

        for piece in pieces:
            p, qty = piece  # `p` è un oggetto MarkedPiece
            mark = p.mark   # Accedi alla marca dall'attributo `mark`
            length = self._get_piece_length(p)
            
            if length > self.stock_length:
                full_length = self.stock_length
                remaining_length = length - self.stock_length

                if mark:  # Usa la marca fornita
                    full_mark = f"{mark}/FULL"
                    comp_mark = f"{mark}/COMP"
                else:  # Genera marche fittizie
                    base_mark = f"'''${processed_count}'''"
                    full_mark = f"{base_mark}/FULL"
                    comp_mark = f"{base_mark}/COMP"
                    processed_count += 1

                # Aggiungi i pezzi suddivisi
                processed.append((MarkedPiece(full_length, full_mark), qty))
                processed.append((MarkedPiece(remaining_length, comp_mark), qty))

                # Aggiorna `joint_combinations`
                joint_key = f"{full_length:.2f} + {remaining_length:.2f}"
                self.joint_combinations[joint_key] = self.joint_combinations.get(joint_key, 0) + qty
            else:
                # Aggiungi i pezzi normali direttamente
                processed.append(piece)
        
        return processed



    def _update_cuts_dict(self, combination: JointCombination, target_length: float):
        #print("\nDEBUG joint_combinations prima dell'aggiornamento:")
        for k, v in dict(self.joint_combinations).items():
            print(f"  {k}: {v}")

        n = len(combination.bar_indices)
        first_cut = combination.wastes[0]
        middle_cuts = combination.wastes[1:-1]
        remaining_length = target_length - first_cut - sum(middle_cuts) + (n-len(combination.bar_indices))*self.blade_width
        
        cuts_list = sorted([first_cut] + middle_cuts + [remaining_length])
        joint_key = " + ".join(f"{cut:.2f}" for cut in cuts_list)
        self.joint_combinations[joint_key] += 1

        # Determina il mark base per tutti i pezzi di questa combinazione
        original_mark = (self.max_waste_bar[0][0].mark or "") if self.max_waste_bar[0] else ""
        mark_prefix = f"{original_mark}/" if original_mark else ""
        joint_mark = f"{mark_prefix}J/{n}"  # Ora creiamo un unico mark per tutti i pezzi

        for i, (bar_idx, waste) in enumerate(zip(combination.bar_indices, combination.wastes)):
            cuts, _ = self._cuts_dict[bar_idx]
            
            # Assegna lo stesso mark a tutti i pezzi della combinazione
            new_cut = MarkedPiece(
                waste if i < n-1 else remaining_length,
                joint_mark  # Usa lo stesso mark per tutti i pezzi
            )

            new_waste = 0 if i < n-1 else combination.wastes[-1] - remaining_length - self.blade_width
            self._cuts_dict[bar_idx] = (list(cuts) + [new_cut], new_waste)
        
        if self.max_waste_index in self._cuts_dict:
            del self._cuts_dict[self.max_waste_index]

        # print("\nDEBUG joint_combinations dopo l'aggiornamento:")
        # for k, v in dict(self.joint_combinations).items():
        #     print(f"  {k}: {v}")       

    def _should_exclude_piece(self, piece) -> bool:
        """Determina se un pezzo deve essere escluso dalle giunzioni"""
        # Verifica FULL
        if isinstance(piece, MarkedPiece) and piece.mark is not None and 'FULL' in piece.mark:
            return True

        if not self._original_pieces or not self.excluded_to_joint:
            return False

        current_length = piece.length
        current_mark = piece.mark

        for idx in self.excluded_to_joint:
            if idx >= len(self._original_pieces):
                continue
                
            excluded_piece = self._original_pieces[idx]
            excluded_length = excluded_piece[0]
            excluded_mark = excluded_piece[2] if len(excluded_piece) > 2 else None
            
            # Se il pezzo escluso ha un mark, richiedi corrispondenza esatta
            if excluded_mark is not None:
                if abs(current_length - excluded_length) < 0.01 and current_mark == excluded_mark:
                    return True
            # Se il pezzo escluso non ha mark, confronta solo lunghezza
            else:
                if abs(current_length - excluded_length) < 0.01:
                    return True
                    
        return False

    def _find_eligible_cuts(self):
        """
        Find all cuts longer than longer_than across all bars, but only from bars
        containing a single piece plus waste.
        Returns a list of tuples (bar_index, cut, cut_index)
        """
        eligible_cuts = []
        #print("\nAnalisi dei tagli eleggibili:")
        #print(f"Indici esclusi: {self.excluded_to_joint}")
        
        for bar_idx, (cuts, waste) in self._cuts_dict.items():
            # Considera solo barre con un singolo pezzo
            if len(cuts) != 1:
                continue
                
            cut = cuts[0]  # c'è solo un pezzo
            length = self._get_piece_length(cut)
            mark = self._get_piece_mark(cut) if isinstance(cut, MarkedPiece) else None
            
            # Skip if this cut should be excluded
            if self._should_exclude_piece(cut):
                #print(f"  Escluso: L={length:.2f}" + (f" ({mark})" if mark else ""))
                continue
                
            if length >= self.longer_than:
                #print(f"  Incluso: L={length:.2f}" + (f" ({mark})" if mark else ""))
                eligible_cuts.append((bar_idx, cut, 0))  # cut_index è sempre 0
        
        sorted_cuts = sorted(eligible_cuts, key=lambda x: self._get_piece_length(x[1]), reverse=True)
        #print(f"\nTotale tagli eleggibili: {len(sorted_cuts)}")
        return sorted_cuts


    def _calculate_statistics(self, patterns: List[CuttingPattern], remaining: Dict[MarkedPiece, int]):
        self.patterns = patterns
        self.remaining = remaining
        self.total_waste = 0
        self.piece_counts = Counter()
        
        #print("\nDEBUG Analisi pezzi:")
        for pattern in patterns:
            self.total_waste += pattern.waste
            for cut in pattern.cuts:
                length = cut.length
                mark = cut.mark
                
                should_count = True
                if mark is not None and any(x in mark for x in ['FULL', '/2', '/J/', 'J/', 'COMP']):
                    should_count = False
                    
                #print(f"  Pezzo: L={length:.2f}" + (f", mark={mark}" if mark else " (no mark)") + 
                #    f" -> {'aggiunto' if should_count else 'ignorato'}")
                
                if should_count:
                    self.piece_counts[length] += 1





    def optimize_with_waste(self, pieces, longer_than):
        # Trova lunghezze duplicate e assegna marche fittizie se necessario
        length_counts = Counter(piece[0] for piece in pieces)
        marked_pieces = []
        
        for piece in pieces:
            length, qty = piece[:2]
            mark = piece[2] if len(piece) == 3 else None
            
            # Se ci sono duplicati e il pezzo non ha già una marca, assegna una marca fittizia
            if length_counts[length] > 1 and mark is None:
                mark = f"'''$'''{length_counts[length]}"
                length_counts[length] -= 1
            
            marked_pieces.append((length, qty, mark))

        # Normalizza i pezzi in MarkedPiece
        normalized_pieces = [
            (MarkedPiece(length, mark), qty) for length, qty, mark in marked_pieces
        ]
        
        self._original_pieces = pieces
        self.longer_than = longer_than 

        # Se abbiamo un pezzo temporaneo da escludere, trova il suo indice
        if hasattr(self, '_temp_excluded_piece'):
            for i, piece in enumerate(pieces):
                if piece[0] == self._temp_excluded_piece[0] and piece[1] == self._temp_excluded_piece[1]:
                    self.excluded_to_joint = [i]
                    break
            delattr(self, '_temp_excluded_piece')

        # Log dei pezzi esclusi
        if self.excluded_to_joint:
            for idx in self.excluded_to_joint:
                if idx < len(pieces):
                    piece = pieces[idx]

        # Processa i pezzi sovradimensionati con il nuovo sistema di tracking
        processed_pieces = self._process_oversize_pieces(normalized_pieces)
        patterns, remaining = super().optimize(processed_pieces)
        self._generate_cuts_dict(patterns)
        
        while True:
            self.iteration += 1
            
            # Trova tutti i tagli eleggibili
            eligible_cuts = self._find_eligible_cuts()
            if not eligible_cuts:
                print("\nNessun taglio più lungo della soglia trovato. Terminazione.")
                break
                
            # Prova a trovare combinazioni per ogni taglio eleggibile
            found_combination = False
            for bar_idx, cut, _ in eligible_cuts:
                target_length = cut.length
                print(f"\nAnalizzando taglio di lunghezza: {target_length:.2f}")
                
                self.max_waste_index = bar_idx
                self.max_waste_bar = self._cuts_dict[bar_idx]
                
                for n_joints in range(2, self.max_joints + 1):
                    combinations = self._find_waste_combinations_n(target_length, n_joints)
                    if combinations:
                        print(f"\nTrovata combinazione valida con {n_joints} giunzioni")
                        self._update_cuts_dict(combinations[0], target_length)
                        found_combination = True
                        break
                
                if found_combination:
                    break
            
            if not found_combination:
                print("\nNessuna combinazione valida trovata. Terminazione.")
                break

        # Crea i pattern finali
        final_patterns = [CuttingPattern(cuts, waste) 
                for cuts, waste in self._cuts_dict.values()]
                
        return final_patterns, remaining

    
    def _print_or_display(self, text: str, output_widget=None):
        """
        Gestisce l'output del testo sia su console che su widget tkinter.
        """
        print(text)  # Stampa sempre su console
        if output_widget:
            try:
                output_widget.configure(state='normal')
                output_widget.insert('end', text + '\n')
                output_widget.configure(state='disabled')
                output_widget.see('end')

            except Exception as e:
                print(f"Errore nella visualizzazione su widget: {e}")

    def print_solution(self, patterns: List[CuttingPattern], remaining: Dict[Union[float, MarkedPiece], int], output_widget=None):
        if not patterns:
            self._print_or_display("\nNo solution found!", output_widget)
            return
            
        self._calculate_statistics(patterns, remaining)

        self._print_or_display(f"\nOptimized Cutting Solution:", output_widget)
        self._print_or_display(f"Stock Length: {self.stock_length}mm", output_widget)
        self._print_or_display(f"Blade Width: {self.blade_width}mm", output_widget)
        self._print_or_display(f"Max Joints: {self.max_joints}", output_widget)
        self._print_or_display("\nCutting Patterns:", output_widget)

        # Creiamo un dizionario dei mark originali
        original_marks = {}
        if self._original_pieces:
            for piece in self._original_pieces:
                if len(piece) > 2:  # se ha un mark originale
                    original_marks[piece[0]] = piece[2]

        for i, pattern in enumerate(patterns, 1):
            self._print_or_display(f"\nBar {i}:", output_widget)
            
            cuts_str = []
            for cut in pattern.cuts:
                length = self._get_piece_length(cut)
                current_mark = self._get_piece_mark(cut)
                
                # Determiniamo se mostrare il mark
                show_mark = None
                
                # Caso 1: il pezzo ha un mark corrente
                if current_mark:
                    show_mark = current_mark
                # Caso 2: il pezzo aveva un mark originale
                elif length in original_marks:
                    show_mark = original_marks[length]
                
                # Costruiamo la stringa del taglio
                if show_mark:
                    cuts_str.append(f"{length:.2f}({show_mark})")
                else:
                    cuts_str.append(f"{length:.2f}")
                
            self._print_or_display(f"  Cuts: {', '.join(cuts_str)}", output_widget)
            self._print_or_display(f"  Number of cuts: {len(pattern.cuts)}", output_widget)
            self._print_or_display(f"  Waste: {pattern.waste:.2f}mm", output_widget)
            self._print_or_display(f"  Usage: {((self.stock_length - pattern.waste) / self.stock_length * 100):.1f}%", output_widget)

    def print_summary(self, patterns: List[CuttingPattern], remaining: Dict[Union[float, MarkedPiece], int], output_widget=None):
        self._calculate_statistics(patterns, remaining)

        self._print_or_display(f"\nSummary:", output_widget)
        self._print_or_display(f"Total bars needed: {len(self.patterns)}", output_widget)
        self._print_or_display(f"Total waste: {self.total_waste:.2f}mm", output_widget)
        self._print_or_display(f"Average waste per bar: {(self.total_waste/len(self.patterns)):.2f}mm", output_widget)
        self._print_or_display(f"Overall material usage: {((len(self.patterns)*self.stock_length - self.total_waste)/(len(self.patterns)*self.stock_length) * 100):.1f}%", output_widget)

        # Raccogliamo tutte le lunghezze usate nelle combinazioni
        joint_lengths = set()
        for joint_key in self.joint_combinations:
            joint_lengths.update(float(x) for x in joint_key.split(" + "))

        self._print_or_display("\nPiece counts:", output_widget)
        # Prima stampa i pezzi normali che non sono in joint_lengths
        for length, count in sorted(self.piece_counts.items()):
            if length not in joint_lengths:
                self._print_or_display(f"  Length {length:.2f}mm: {count} pieces", output_widget)
            else:
                # Pezzi singoli che hanno stessa lunghezza di parti giuntate
                self._print_or_display(f"  Length {length:.2f}mm: {count} pieces", output_widget)

        # Poi stampa le combinazioni
        for joint_key, count in sorted(self.joint_combinations.items()):
            parts = [float(x) for x in joint_key.split(" + ")]
            total = sum(parts)
            self._print_or_display(f"  Length {joint_key}mm = {total:.2f}: {count} pieces", output_widget)

    def generate_pdf(self, filename="cutting_list.pdf", profilo='MIO PROFILO', commessa='Cxxx', num_columns=2):
        """
        Genera un PDF della distinta di taglio usando CuttingListPDF
        """
        self.profilo = profilo
        self.commessa = commessa

        if not self.patterns:
            raise ValueError("Nessun pattern disponibile. Esegui prima l'ottimizzazione.")
            
        pdf = CuttingListPDF(filename, profilo=self.profilo, commessa=self.commessa, num_columns=num_columns)
        pdf._add_header()
        
        for i, pattern in enumerate(self.patterns, 1):
            cuts = [(self._get_piece_length(cut), self._get_piece_mark(cut))
                    for cut in pattern.cuts]
            pdf.add_bar_section(i, cuts)  # Rimosso self.stock_length
        
        pdf.save()


if __name__ == '__main__':
    longer_than = 4500
    stock_length = 6000
    blade_width = 2
    pieces = [
    (8535, 9, 'P10'),   # sovradimensionato
    (7807, 6, 'P14'),    # normale
    (1200, 5, 'P15'),    # può essere giuntato
    (948, 5, 'P18'),           # stesso ma senza mark
    (7807, 2, 'P19'),           # stesso ma senza mark
    (1207, 1, 'P20'),           # stesso ma senza mark
 ]

#     pieces = [
#     (8535, 9),   # sovradimensionato
#     (7807, 2),    # normale
#     (1200, 5),    # può essere giuntato
#     (948, 5),           # stesso ma senza mark
#     (7807, 6),           # stesso ma senza mark
#     (1207, 1),           # stesso ma senza mark
# ]

    # pieces = [
    #     (8535, 9, 'P10'),   # sovradimensionato
    #     (7807, 2, 'P12'),    # normale
    #     (1200, 5, 'P11'),    # può essere giuntato
    #     (948, 5),           # stesso ma senza mark
    #     (7807, 6),           # stesso ma senza mark
    #     (1207, 1),           # stesso ma senza mark
    # ]
    excluded_pieces = 0, 1, -2
    #print(pieces[-2])
    #excluded_pieces = pieces[0] 
    excluded_pieces = [] 
    # print(excluded_pieces)
    ordered_pieces = sorted(pieces, key=lambda x: x[0], reverse=True)

    cuts = WasteCuttingStockOptimizer(stock_length, blade_width, max_joints=3, excluded_to_joint=excluded_pieces)
    patterns, remaining = cuts.optimize_with_waste(pieces, longer_than)
    cuts.print_solution(patterns, remaining)
    cuts.print_summary(patterns, remaining)
    cuts.generate_pdf("mia_distinta.pdf")
