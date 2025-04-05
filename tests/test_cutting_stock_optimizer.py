import unittest
from collections import Counter
import sys
from io import StringIO
import time
from cutting_stock_optimizer import StrictCuttingStockOptimizer, CuttingPattern

class TestStrictCuttingStockOptimizer(unittest.TestCase):
    def setUp(self): 
        """Setup comune per i test."""
        self.stock_length = 12000
        self.blade_width = 3
        self.optimizer = StrictCuttingStockOptimizer(self.stock_length, self.blade_width)

    def test_001_comparison_excel_output(self):
        """Test: Confronta i risultati dell'algoritmo con un output specifico."""

        # Crea l'oggetto optimizer con i parametri giusti al momento della creazione
        self.optimizer = StrictCuttingStockOptimizer(stock_length=12000, blade_width=2)


        test_pieces = [
            (2814.22, 2), (2907.09, 2), (2908.38, 2), (2908.57, 2), (3160.48, 4),
            (3165.52, 2), (3248.34, 2), (3260.24, 2), (3267.24, 2), (3310.53, 2),
            (3322.07, 2), (3380.57, 4), (3456.12, 2), (3668.29, 2), (3731.22, 2),
            (3738.22, 4), (3763.80, 2), (4298.21, 2),
        ]
        
        # Ottimizza il taglio
        patterns, _ = self.optimizer.optimize(test_pieces)

        # Risultato atteso
        expected_output = [
            (['4298.21', '4298.21', '3380.57'], 17.01),
            (['3763.80', '3763.80', '3738.22'], 728.18),
            (['3738.22', '3738.22', '3738.22'], 779.34),
            (['3731.22', '3731.22', '3668.29'], 863.27),
            (['3668.29', '3456.12', '3456.12'], 1413.47),
            (['3380.57', '3380.57', '3380.57'], 1852.29),
            (['3322.07', '3322.07', '3310.53'], 2039.33),
            (['3310.53', '3267.24', '3267.24'], 2148.99),
            (['3260.24', '3260.24', '3248.34'], 2225.18),
            (['3248.34', '3165.52', '3165.52'], 2414.62),
            (['3160.48', '3160.48', '3160.48'], 2512.56),
            (['3160.48', '2908.57', '2908.57', '2908.38'], 106.00),
            (['2908.38', '2907.09', '2907.09', '2814.22'], 455.22),
            (['2814.22'], 9183.78),
        ]
        
        # Verifica
        for (expected_cuts, expected_waste), pattern in zip(expected_output, patterns):
            # Confronta i tagli
            self.assertEqual(
                [f"{cut:.2f}" for cut in pattern.cuts],
                expected_cuts,
                f"FAIL: Expected cuts {expected_cuts}, but got {pattern.cuts}",
            )
            # Confronta lo scarto con una tolleranza
            self.assertAlmostEqual(
                pattern.waste,
                expected_waste,
                places=2,
                msg=f"FAIL: Expected waste {expected_waste:.2f}, but got {pattern.waste:.2f}",
            )

    def test_002_too_long_pieces(self):
        """Test for pieces longer than stock length"""
        self.optimizer = StrictCuttingStockOptimizer(stock_length=12000, blade_width=3)
        test_pieces = [(13000, 1), (5000, 1)]
        
        # Redireziona l'output di print_solution su un buffer per verificare il contenuto
        captured_output = StringIO()
        sys.stdout = captured_output
        
        # Ottimizza i pezzi
        patterns, remaining = self.optimizer.optimize(test_pieces)
        self.optimizer.print_solution(patterns, remaining)
        
        # Ripristina stdout
        sys.stdout = sys.__stdout__
        
        # Verifica che il messaggio di warning sia presente nell'output
        output = captured_output.getvalue()
        expected_warning = "WARNING - Remaining pieces that couldn't be fit:"
        self.assertIn(expected_warning, output,
                    "FAIL: Expected warning for too-long pieces was not printed.")
        
        # Verifica che il pezzo troppo lungo non sia incluso nei pattern
        self.assertEqual(len(patterns), 1, "FAIL: Expected 1 pattern (for the 5000mm piece), but got more.")
        self.assertNotIn(13000, [cut for pattern in patterns for cut in pattern.cuts],
                        "FAIL: The too-long piece was incorrectly included in a pattern.")
        
        # Verifica che il pezzo lungo sia nella lista dei rimanenti
        self.assertIn(13000, remaining, "FAIL: The too-long piece is missing from remaining pieces.")
        self.assertEqual(remaining[13000], 1, "FAIL: The too-long piece quantity is incorrect.")

    def test_003_close_to_stock_limit(self):
        """Test: pezzi che lasciano poco spazio per la lama."""
        pieces = [(5998, 2), (3000, 1)]
        patterns, remaining = self.optimizer.optimize(pieces)
        total_waste = sum(pattern.waste for pattern in patterns)
        
        self.assertGreaterEqual(total_waste, 0, 
            f"FAIL: Total waste should be non-negative, but got {total_waste}")
        self.assertEqual(len(patterns), 2, 
            f"FAIL: Expected 2 patterns for close-to-limit pieces, but got {len(patterns)}")
        self.assertEqual(remaining[5998], 0, 
            f"FAIL: All 5998mm pieces should be used, but {remaining[5998]} remained")
        self.assertEqual(remaining[3000], 0, 
            f"FAIL: All 3000mm pieces should be used, but {remaining[3000]} remained")

    def test_004_high_frequency_short_pieces(self):
        """Test: molti pezzi corti."""
        pieces = [(50, 100), (1000, 1), (400, 2)]
        patterns, remaining = self.optimizer.optimize(pieces)
        total_pieces_cut = sum(len(pattern.cuts) for pattern in patterns)
        
        self.assertEqual(total_pieces_cut, 103, 
            f"FAIL: Expected 103 total pieces cut, but got {total_pieces_cut}")
        self.assertEqual(remaining[50], 0, 
            f"FAIL: All 50mm pieces should be used, but {remaining[50]} remained")
        self.assertEqual(remaining[1000], 0, 
            f"FAIL: All 1000mm pieces should be used, but {remaining[1000]} remained")
        self.assertEqual(remaining[400], 0, 
            f"FAIL: All 400mm pieces should be used, but {remaining[400]} remained")


    def test_005_no_solution_possible(self):
        """Test: pezzi che non si adattano completamente senza spreco."""
        pieces = [(12000, 1), (15000, 1)]
        patterns, remaining = self.optimizer.optimize(pieces)
        
        self.assertEqual(len(patterns), 1, 
            f"FAIL: Expected 1 pattern for no solution case, but got {len(patterns)}")
        self.assertEqual(remaining[15000], 1, 
            f"FAIL: 15000mm piece should remain uncut, but got {remaining[15000]}")
        if patterns:
            self.assertEqual(patterns[0].waste, 0, 
                f"FAIL: Expected 0 waste for 12000mm piece, but got {patterns[0].waste}")

    def test_006_invalid_piece_quantities(self):
        """Test: quantità negativa o zero."""
        pieces = [(500, -2), (1000, 0), (3000, 3)]
        patterns, remaining = self.optimizer.optimize(pieces)
        
        self.assertEqual(len(patterns), 1, 
            f"FAIL: Expected 1 pattern for valid pieces, but got {len(patterns)}")
        self.assertEqual(remaining[500], -2, 
            f"FAIL: Negative quantities should remain unchanged, but got {remaining[500]}") 
        self.assertEqual(remaining[1000], 0, 
            f"FAIL: Zero quantities should remain unchanged, but got {remaining[1000]}")
        self.assertEqual(remaining[3000], 0, 
            f"FAIL: All 3000mm pieces should be used, but {remaining[3000]} remained")

    def test_007_large_input_set(self):
        """Test: comportamento con un grande set di dati (>15 pezzi)."""
        pieces = [
            (400, 10),   # 10 pezzi da 400mm
            (1000, 5),   # 5 pezzi da 1000mm
            (2000, 3),   # 3 pezzi da 2000mm
            (300, 20),   # 20 pezzi da 300mm
            (500, 7),    # 7 pezzi da 500mm
            (1500, 2),   # 2 pezzi da 1500mm
            (2500, 4),   # 4 pezzi da 2500mm
            (600, 12),   # 12 pezzi da 600mm
            (1200, 6),   # 6 pezzi da 1200mm
            (800, 8),    # 8 pezzi da 800mm
            (700, 9),    # 9 pezzi da 700mm
            (1800, 2),   # 2 pezzi da 1800mm
            (4000, 1),   # 1 pezzo da 4000mm
            (50, 50),    # 50 pezzi da 50mm
            (950, 4)     # 4 pezzi da 950mm
        ]
        
        patterns, remaining = self.optimizer.optimize(pieces)

        # Verifica che tutti i pezzi siano stati tagliati correttamente
        total_requested = sum(qty for _, qty in pieces)
        total_cut = sum(len(pattern.cuts) for pattern in patterns)
        self.assertEqual(total_requested, total_cut, 
            f"FAIL: Total requested pieces ({total_requested}) do not match total cut pieces ({total_cut})")

        # Verifica che nessun pezzo sia rimasto inutilizzato
        for length, qty in remaining.items():
            self.assertEqual(qty, 0, 
                f"FAIL: Remaining pieces for length {length}mm should be 0 but are {qty}")

        # Verifica che il numero di pattern sia ragionevole
        self.assertLess(len(patterns), total_requested, 
            f"FAIL: Too many patterns generated ({len(patterns)}) for {total_requested} pieces")

        # Controlla che lo spreco complessivo sia accettabile
        total_waste = sum(pattern.waste for pattern in patterns)
        self.assertGreaterEqual(total_waste, 0, 
            f"FAIL: Total waste should be non-negative, but it's {total_waste}")
        max_waste = len(patterns) * self.stock_length
        self.assertLess(total_waste, max_waste, 
            f"FAIL: Total waste ({total_waste}) should be less than available stock ({max_waste})")

class CompactTestRunner(unittest.TextTestRunner):
    def __init__(self, stream=None, descriptions=True, verbosity=1):
        super().__init__(stream, descriptions, verbosity)
        self.stream = stream or sys.stderr

    def run(self, test):
        result = CompactTestResult(self.stream, self.descriptions, self.verbosity)
        startTime = time.time()  # Use time.time() instead of unittest.time.time()
        test(result)
        stopTime = time.time()  # Use time.time() to get the end time
        timeTaken = stopTime - startTime

        result.printCompactResults()
        self.stream.write(f"\nTime: {timeTaken:.3f}s")
        
        if not result.wasSuccessful():
            self.stream.write("\nFailures:\n")
            for failure in result.failures + result.errors:
                self.stream.write(f"\n{failure[0]}")
                self.stream.write("-" * 70)
                self.stream.write(failure[1])
        
        return result

class CompactTestResult(unittest.TestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.stream = stream
        self.test_results = []
        
    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_results.append('.')
        
    def addError(self, test, err):
        super().addError(test, err)
        self.test_results.append('E')
        
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_results.append('F')
        
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_results.append('S')
        
    def printCompactResults(self):
        self.stream.write(''.join(self.test_results))  # Use write instead of writeln
        summary = []
        if self.failures:
            summary.append(f"failures={len(self.failures)}")
        if self.errors:
            summary.append(f"errors={len(self.errors)}")
        if self.skipped:
            summary.append(f"skipped={len(self.skipped)}")
            
        tests_run = self.testsRun
        self.stream.write(f"\n\nRan {tests_run} tests")  # Use write instead of writeln
        if summary:
            self.stream.write(f"FAILED ({', '.join(summary)})")  # Use write instead of writeln
        else:
            self.stream.write("OK")  # Use write instead of writeln


if __name__ == "__main__":
    # Usa il nuovo runner personalizzato
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStrictCuttingStockOptimizer)
    runner = CompactTestRunner(verbosity=1)
    result = runner.run(suite)
