from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from datetime import datetime
import math

class CuttingListPDF:
    def __init__(self, filename="cutting_list.pdf", num_columns=3, profilo='MIO PROFILO', commessa='Cxxx'):
        self.profilo = profilo
        self.commessa = commessa
        self.page_width, self.page_height = landscape(A4)
        self.c = canvas.Canvas(filename, pagesize=landscape(A4))
        
        # Configurazione colonne
        self.num_columns = max(1, min(num_columns, 4))
        self.current_column = 0
        
        # Margini e dimensioni di base
        self.margin = 20*mm
        self.column_spacing = 10*mm
        
        # Calcoliamo la larghezza disponibile e quella delle colonne
        usable_width = self.page_width - (2 * self.margin) - ((self.num_columns - 1) * self.column_spacing)
        self.box_width = usable_width / self.num_columns
        
        # Dimensioni standard
        self.line_height = 8*mm
        self.checkbox_size = 4*mm
        self.box_top_margin = 6*mm
        self.box_bottom_margin = -2*mm
        
        # Configurazione colonne interne
        self.max_cuts_per_column = 18
        self.min_column_width = 60*mm
        self.internal_spacing = 5*mm
        
        # Calcoliamo le posizioni X di tutte le colonne
        self.column_positions = []
        for i in range(self.num_columns):
            x_pos = (self.margin + 
                    (i * self.box_width) + 
                    (i * self.column_spacing))
            self.column_positions.append(x_pos)
        
        self.y = self.page_height - self.margin
        
    def _add_header(self):
        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawString(self.margin, self.page_height - 15*mm, "DISTINTA DI TAGLIO")
        self.c.drawString(self.margin + 60*mm, self.page_height - 15*mm, self.profilo)
        self.c.drawString(self.page_width - 90*mm, self.page_height - 15*mm, self.commessa)
        
        current_date = datetime.now().strftime("%d/%m/%Y")
        self.c.setFont("Helvetica", 10)
        self.c.drawString(self.page_width - 60*mm, self.page_height - 15*mm, current_date)
        
        self.c.line(self.margin, self.page_height - 20*mm,
                   self.page_width - self.margin, self.page_height - 20*mm)
        
        self.y = self.page_height - 30*mm
        
    def _new_page(self):
        self.c.showPage()
        self.y = self.page_height - self.margin
        self.current_column = 0
        self._add_header()

    def _check_space(self, height_needed, width_needed=None):
        """Controlla se c'è spazio sufficiente nella colonna corrente"""
        if width_needed and width_needed > self.box_width:
            # Se la larghezza necessaria è maggiore della colonna corrente,
            # andiamo a capo pagina
            self._new_page()
            return True
            
        if self.y - height_needed < self.margin:
            if self.current_column < self.num_columns - 1:
                self.current_column += 1
                self.y = self.page_height - 30*mm
            else:
                self._new_page()
            return True
        return False

    def add_bar_section(self, bar_number, cuts):
        if len(cuts) <= self.max_cuts_per_column:
            # Gestione normale per pochi tagli
            content_height = (len(cuts) * self.line_height) + (2 * self.line_height)
            total_box_height = content_height + self.box_top_margin + self.box_bottom_margin
            
            self._check_space(total_box_height)
            
            current_x = self.column_positions[self.current_column]
            initial_y = self.y
            
            # Disegna il box
            self.c.rect(current_x, self.y - total_box_height, self.box_width, total_box_height)
            
            self.y -= self.box_top_margin
            
            # Intestazione barra
            self.c.setFont("Helvetica-Bold", 14)
            self.c.drawString(current_x + 2*mm, self.y, f"Barra {bar_number}")
            self.y -= self.line_height * 1.2
            
            # Intestazioni colonne
            self.c.setFont("Helvetica-Bold", 12)
            self.c.drawString(current_x + 4*mm, self.y, "LUNGH")
            self.c.drawString(current_x + self.box_width/2 - 5*mm, self.y, "MARCA")
            self.y -= self.line_height * 1.1
            
            # Tagli
            self.c.setFont("Helvetica", 12)
            for length, mark in cuts:
                self.c.drawString(current_x + 4*mm, self.y, f"{length:>6.0f}")
                
                if mark:
                    self.c.setFont("Courier-Oblique", 12)
                    self.c.drawString(current_x + self.box_width/2 - 5*mm, self.y, f"'{mark}'")
                    self.c.setFont("Helvetica", 12)
                
                self.c.rect(current_x + self.box_width - 10*mm, self.y, 
                           self.checkbox_size, self.checkbox_size)
                
                self.y -= self.line_height
            
            self.y = initial_y - total_box_height - 2*mm
            
        else:
            # Calcolo del numero di colonne interne necessarie
            num_internal_columns = math.ceil(len(cuts) / self.max_cuts_per_column)
            
            # Calcolo della larghezza totale necessaria
            total_box_width = (self.min_column_width * num_internal_columns) + \
                            (self.internal_spacing * (num_internal_columns - 1))
            
            # Calcolo dell'altezza necessaria
            content_height = (self.max_cuts_per_column * self.line_height) + (2 * self.line_height)
            total_box_height = content_height + self.box_top_margin + self.box_bottom_margin
            
            # Controlliamo se c'è abbastanza spazio
            self._check_space(total_box_height, total_box_width)
            
            current_x = self.column_positions[self.current_column]
            initial_y = self.y
            
            # Disegniamo il box principale
            self.c.rect(current_x, self.y - total_box_height, 
                       total_box_width, total_box_height)
            
            # Aggiungiamo il titolo della barra
            self.y -= self.box_top_margin
            self.c.setFont("Helvetica-Bold", 14)
            self.c.drawString(current_x + 2*mm, self.y, f"Barra {bar_number}")
            self.y -= self.line_height * 1.2
            
            # Per ogni colonna interna
            for col in range(num_internal_columns):
                column_x = current_x + (col * (self.min_column_width + self.internal_spacing))
                column_y = self.y
                
                # Intestazioni colonne
                self.c.setFont("Helvetica-Bold", 12)
                self.c.drawString(column_x + 4*mm, column_y, "LUNGH")
                self.c.drawString(column_x + self.min_column_width/2 - 5*mm, column_y, "MARCA")
                column_y -= self.line_height * 1.1
                
                # Tagli per questa colonna
                start_idx = col * self.max_cuts_per_column
                end_idx = min((col + 1) * self.max_cuts_per_column, len(cuts))
                
                self.c.setFont("Helvetica", 12)
                for length, mark in cuts[start_idx:end_idx]:
                    self.c.drawString(column_x + 4*mm, column_y, f"{length:>6.0f}")
                    
                    if mark:
                        self.c.setFont("Courier-Oblique", 12)
                        self.c.drawString(column_x + self.min_column_width/2 - 5*mm, column_y, f"'{mark}'")
                        self.c.setFont("Helvetica", 12)
                    
                    self.c.rect(column_x + self.min_column_width - 10*mm, column_y, 
                              self.checkbox_size, self.checkbox_size)
                    
                    column_y -= self.line_height
            
            self.y = initial_y - total_box_height - 2*mm

    def save(self):
        self.c.save()