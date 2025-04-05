from typing import List, Tuple, Dict, Union, Optional
from dataclasses import dataclass
from collections import Counter

@dataclass(frozen=True) 
class MarkedPiece:
    length: float
    mark: Optional[str] = None
    
    def __hash__(self):
        return hash((self.length, self.mark))
    
    def __eq__(self, other):
        if not isinstance(other, MarkedPiece):
            return NotImplemented
        return self.length == other.length and self.mark == other.mark

@dataclass
class CuttingPattern:
    cuts: List[Union[float, MarkedPiece]]
    waste: float

class StrictCuttingStockOptimizer:
    def __init__(self, stock_length: float, blade_width: float):
        self.stock_length = stock_length
        self.blade_width = blade_width
        
    def _calculate_waste(self, cuts: List[Union[float, MarkedPiece]]) -> float:
        if not cuts:
            return self.stock_length
        total_length = sum(cut.length if isinstance(cut, MarkedPiece) else cut for cut in cuts)
        total_length += len(cuts) * self.blade_width
        return max(0, self.stock_length - total_length)
    
    def _can_fit(self, current_cuts: List[Union[float, MarkedPiece]], new_cut: Union[float, MarkedPiece]) -> bool:
        if not current_cuts:
            cut_length = new_cut.length if isinstance(new_cut, MarkedPiece) else new_cut
            return cut_length <= self.stock_length
        
        total_length = sum(cut.length if isinstance(cut, MarkedPiece) else cut for cut in current_cuts)
        cut_length = new_cut.length if isinstance(new_cut, MarkedPiece) else new_cut
        total_length += cut_length
        blade_space = len(current_cuts) * self.blade_width
        return total_length + blade_space <= self.stock_length
        
    def _find_best_pattern(self, remaining_pieces: Dict[Union[float, MarkedPiece], int]) -> List[Union[float, MarkedPiece]]:
        pattern = []
        remaining = remaining_pieces.copy()
        
        sorted_pieces = sorted(
            [(piece, qty) for piece, qty in remaining.items() if qty > 0],
            key=lambda x: (-(x[0].length if isinstance(x[0], MarkedPiece) else x[0]))
        )
        
        for piece, _ in sorted_pieces:
            while (remaining[piece] > 0 and 
                   self._can_fit(pattern, piece)):
                test_pattern = pattern + [piece]
                new_waste = self._calculate_waste(test_pattern)
                
                if new_waste >= 0:
                    pattern.append(piece)
                    remaining[piece] -= 1
                else:
                    break
                    
        return pattern
    
    def optimize(self, pieces: List[Union[Tuple[float, int], Tuple[float, int, str]]]) -> Tuple[List[CuttingPattern], Dict[Union[float, MarkedPiece], int]]:
        # Convert input pieces to MarkedPiece if mark is provided
        processed_pieces = []
        for piece in pieces:
            if len(piece) == 3:
                length, qty, mark = piece
                processed_pieces.append((MarkedPiece(length, mark), qty))
            else:
                length, qty = piece
                processed_pieces.append((length, qty))

        too_long_pieces = [
            piece for piece, _ in processed_pieces
            if (piece.length if isinstance(piece, MarkedPiece) else piece) > self.stock_length
        ]
        
        if too_long_pieces:
            print("\nWARNING: The following pieces are too long to fit into the stock and will be skipped:")
            for piece in too_long_pieces:
                length = piece.length if isinstance(piece, MarkedPiece) else piece
                print(f"  - Length: {length:.2f}mm")
        
        filtered_pieces = [
            (piece, qty) for piece, qty in processed_pieces
            if (piece.length if isinstance(piece, MarkedPiece) else piece) <= self.stock_length
        ]
        
        remaining_pieces = dict(filtered_pieces)
        patterns = []
        
        while any(qty > 0 for qty in remaining_pieces.values()):
            current_pattern = self._find_best_pattern(remaining_pieces)
            
            if not current_pattern:
                break
                
            waste = self._calculate_waste(current_pattern)
            patterns.append(CuttingPattern(current_pattern, waste))
            
            for piece in current_pattern:
                remaining_pieces[piece] -= 1

        for piece, qty in processed_pieces:
            if (piece.length if isinstance(piece, MarkedPiece) else piece) > self.stock_length:
                remaining_pieces[piece] = qty
                
        return patterns, remaining_pieces
    
    def print_solution(self, patterns: List[CuttingPattern], remaining: Dict[Union[float, MarkedPiece], int]):
        if not patterns:
            print("\nNo solution found!")
            return
            
        print(f"\nOptimized Cutting Solution:")
        print(f"Stock Length: {self.stock_length}mm")
        print(f"Blade Width: {self.blade_width}mm")
        print("\nCutting Patterns:")
        
        total_waste = 0
        piece_counts = Counter()
        
        for i, pattern in enumerate(patterns, 1):
            total_waste += pattern.waste
            for cut in pattern.cuts:
                piece_counts[cut.length if isinstance(cut, MarkedPiece) else cut] += 1
                
            print(f"\nBar {i}:")
            cuts_str = []
            for cut in pattern.cuts:
                if isinstance(cut, MarkedPiece):
                    cuts_str.append(f"{cut.length:.2f}({cut.mark})")
                else:
                    cuts_str.append(f"{cut:.2f}")
            print(f"  Cuts: {cuts_str}")
            print(f"  Number of cuts: {len(pattern.cuts)}")
            print(f"  Waste: {pattern.waste:.2f}mm")
            print(f"  Usage: {((self.stock_length - pattern.waste) / self.stock_length * 100):.1f}%")
        
        print(f"\nSummary:")
        print(f"Total bars needed: {len(patterns)}")
        print(f"Total waste: {total_waste:.2f}mm")
        print(f"Average waste per bar: {(total_waste/len(patterns)):.2f}mm")
        print(f"Overall material usage: {((len(patterns)*self.stock_length - total_waste)/(len(patterns)*self.stock_length) * 100):.1f}%")
        
        print("\nPiece counts:")
        for length, count in sorted(piece_counts.items()):
            print(f"  Length {length:.2f}mm: {count} pieces")
            
        if any(qty > 0 for qty in remaining.values()):
            print("\nWARNING - Remaining pieces that couldn't be fit:")
            for piece, qty in remaining.items():
                if qty > 0:
                    if isinstance(piece, MarkedPiece):
                        print(f"  Length {piece.length:.2f}mm (Mark: {piece.mark}): {qty} pieces")
                    else:
                        print(f"  Length {piece:.2f}mm: {qty} pieces")


# Example usage
if __name__ == "__main__":
    stock_length = 12000
    blade_width = 3
    pieces = [
        (2300, 12),
        (3850, 5, 'P14'),   
        (4800, 6, 'P15'),   
        (8350, 4, 'P15'), 
        (7430, 4),  
    ]
    
    optimizer = StrictCuttingStockOptimizer(stock_length, blade_width)
    patterns, remaining = optimizer.optimize(pieces)
    optimizer.print_solution(patterns, remaining)