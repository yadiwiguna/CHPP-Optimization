# -*- coding: utf-8 -*-
"""
Created on Sat Aug 24 18:13:07 2024

@author: Yoga
"""

import sys
import os
import pulp
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QGroupBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
import traceback
import logging

logging.basicConfig(filename='app.log', level=logging.DEBUG)

def get_icon_path():
    # Method 1: Use relative path from script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'icons', 'adaro.png')
    
    # Method 2: Look for icon in multiple possible locations
    possible_locations = [
        icon_path,
        os.path.join(script_dir, 'adaro.png'),
        os.path.join(os.path.expanduser('~'), '.config', 'kelanis_optimization_app', 'adaro.png'),
        '/usr/share/icons/kelanis_optimization_app/adaro.png'
    ]
    
    for path in possible_locations:
        if os.path.exists(path):
            return path
    
    print("Peringatan: File ikon tidak ditemukan.")
    return None

class OptimizationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optimisasi Aliran Jaringan Kelanis")
        self.setGeometry(100, 100, 1000, 900)
        
        # Set custom icon with flexible path
        icon_path = get_icon_path()
        if icon_path:
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            # Explicitly set the taskbar icon (Windows-specific)
            if sys.platform.startswith('win'):
                import ctypes
                myappid = 'mycompany.myproduct.subproduct.version'  # arbitrary string
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.hopper_buttons = {}
        self.reclaimer_buttons = {}
        self.outloading_buttons = {}

        # Define attributes
        self.outloading_target = {
            'L4': 1400, 'L6': 1250, 'L26': 1550,
            'L20': 2250, 'L9': 1750, 'L29': 1950
        }

        self.hopper_capacity = {
            'H1': 600, 'H2': 1300, 'H3': 1150, 'H4': 1000,
            'H5': 2300, 'H6': 1350, 'H7': 1450
        }

        self.reclaimer_capacity = {
            'L3': 1050, 'L1': 1100, 'L2': 800, 'L8': 1050,
            'L21': 1450, 'L16': 800, 'L17': 950, 'L18': 1000, 'L19': 800
        }

        self.active_jetties = {}

        self.create_input_section()
        self.create_output_section()

        # Set font size for input widgets
        self.setStyleSheet("""
            QGroupBox { font-size: 10pt; }
            QPushButton { font-size: 9pt; }
        """)

    def create_input_section(self):
        input_group = QGroupBox("Opsi Input")
        input_layout = QVBoxLayout()

        # Hoppers
        hoppers = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7']
        hopper_group = self.create_toggle_buttons(hoppers, "Hoppers")
        input_layout.addWidget(hopper_group)

        # Reclaimers
        reclaimers = ['L3', 'L1', 'L2', 'L8', 'L21', 'L16', 'L17', 'L18', 'L19']
        reclaimer_group = self.create_toggle_buttons(reclaimers, "Reclaimers")
        input_layout.addWidget(reclaimer_group)

        # Outloadings
        outloadings = ['L4', 'L6', 'L26', 'L20', 'L9', 'L29']
        outloading_group = self.create_toggle_buttons(outloadings, "Outloadings")
        input_layout.addWidget(outloading_group)

        # Add Solve and Reset buttons in a horizontal layout
        button_layout = QHBoxLayout()
        self.solve_button = QPushButton("Solve")
        self.solve_button.clicked.connect(self.solve_optimization)
        button_layout.addWidget(self.solve_button)

        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_buttons)
        button_layout.addWidget(self.reset_button)

        input_layout.addLayout(button_layout)

        input_group.setLayout(input_layout)
        self.layout.addWidget(input_group)

    def reset_buttons(self):
        for button_dict in [self.hopper_buttons, self.reclaimer_buttons, self.outloading_buttons]:
            for button in button_dict.values():
                button.setChecked(True)
        self.output_text.clear()
        self.output_text.setStyleSheet("background-color: white; font-size: 9pt; font-family: Courier, monospace;")

    def create_toggle_buttons(self, items, title):
        group = QGroupBox(title)
        layout = QHBoxLayout()
        buttons = {}
        for item in items:
            button = QPushButton(item)
            button.setCheckable(True)
            button.setChecked(True)
            layout.addWidget(button)
            buttons[item] = button
        group.setLayout(layout)
        
        if title == "Hoppers":
            self.hopper_buttons = buttons
        elif title == "Reclaimers":
            self.reclaimer_buttons = buttons
        elif title == "Outloadings":
            self.outloading_buttons = buttons
        
        return group

    def create_output_section(self):
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("font-size: 9pt; font-family: Courier, monospace;")
        self.layout.addWidget(self.output_text)

    def solve_optimization(self):
        try:
            # Get active options
            active_hoppers = [h for h, btn in self.hopper_buttons.items() if btn.isChecked()]
            active_reclaimers = [r for r, btn in self.reclaimer_buttons.items() if btn.isChecked()]
            active_outloadings = [o for o, btn in self.outloading_buttons.items() if btn.isChecked()]

            # Run optimization
            prob, result, status = self.run_optimization(active_hoppers, active_reclaimers, active_outloadings)

            # If status is infeasible, check which constraints are violated
            if status == "Infeasible":
                violated_constraints = self.check_violated_constraints(prob, active_hoppers, active_reclaimers, active_outloadings)
                explanation = "\nPenjelasan ketidaklayakan (infeasibility):\n"
                for constraint in violated_constraints:
                    explanation += f"- {constraint}\n"
                result = explanation + "\n" + result

            # Display results
            self.output_text.setText(result)
            
            # Set background color based on status
            if status == "Infeasible":
                self.output_text.setStyleSheet("background-color: #FFCCCB; font-size: 9pt; font-family: Courier, monospace;")
            else:
                self.output_text.setStyleSheet("background-color: white; font-size: 9pt; font-family: Courier, monospace;")
        except Exception as e:
            error_msg = f"Terjadi kesalahan: {str(e)}\n\nSilakan hubungi tim support dengan menyertakan pesan error ini:\n{traceback.format_exc()}"
            logging.error(error_msg)
            self.output_text.setText(error_msg)
            self.output_text.setStyleSheet("background-color: #FFCCCB; font-size: 9pt; font-family: Courier, monospace;")

    def check_violated_constraints(self, prob, active_hoppers, active_reclaimers, active_outloadings):
        violated_constraints = []

        # Check outloading target constraints
        for o in active_outloadings:
            lower_bound = 0.8 * self.outloading_target[o]
            upper_bound = 1.7 * self.outloading_target[o]
            actual_flow = sum(prob.variablesDict()[f"flow_{h}_{j}_{o}"].varValue 
                            for h in active_hoppers for j in self.active_jetties if o in self.active_jetties[j]) + \
                        sum(prob.variablesDict()[f"reclaim_flow_{r}_{j}_{o}"].varValue 
                            for r in active_reclaimers for j in self.active_jetties if o in self.active_jetties[j])
            if actual_flow < lower_bound:
                violated_constraints.append(f"Outloading {o} di bawah target minimum ({actual_flow:.2f} < {lower_bound:.2f})")
            elif actual_flow > upper_bound:
                violated_constraints.append(f"Outloading {o} melebihi target maksimum ({actual_flow:.2f} > {upper_bound:.2f})")

        # Check hopper and reclaimer capacity constraints
        for h in active_hoppers:
            actual_flow = sum(prob.variablesDict()[f"flow_{h}_{j}_{o}"].varValue 
                            for j in self.active_jetties for o in self.active_jetties[j])
            if actual_flow > self.hopper_capacity[h]:
                violated_constraints.append(f"Hopper {h} melebihi kapasitas ({actual_flow:.2f} > {self.hopper_capacity[h]})")

        for r in active_reclaimers:
            actual_flow = sum(prob.variablesDict()[f"reclaim_flow_{r}_{j}_{o}"].varValue 
                            for j in self.active_jetties for o in self.active_jetties[j])
            if actual_flow > self.reclaimer_capacity[r]:
                violated_constraints.append(f"Reclaimer {r} melebihi kapasitas ({actual_flow:.2f} > {self.reclaimer_capacity[r]})")

        # Check H5 and L8 to L9 constraint
        if 'H5' in active_hoppers and 'L8' in active_reclaimers and 'L9' in active_outloadings:
            h5_to_l9 = prob.variablesDict()["h5_to_l9"].varValue
            l8_to_l9 = prob.variablesDict()["l8_to_l9"].varValue
            if h5_to_l9 + l8_to_l9 > 1:
                violated_constraints.append("H5 dan L8 keduanya mengirim ke L9 secara bersamaan")

        # Check L16 and L21 constraints
        if 'L16' in active_reclaimers and 'L21' in active_reclaimers:
            if 'L29' in active_outloadings and 'L26' in active_outloadings:
                l16_l29 = prob.variablesDict()["reclaimer_use_L16_L29"].varValue
                l21_l26 = prob.variablesDict()["reclaimer_use_L21_L26"].varValue
                l16_l26 = prob.variablesDict()["reclaimer_use_L16_L26"].varValue
                l21_l29 = prob.variablesDict()["reclaimer_use_L21_L29"].varValue
                if l16_l29 + l21_l26 > 1 or l16_l26 + l21_l29 > 1:
                    violated_constraints.append("L16 dan L21 digunakan secara bersamaan untuk outloading yang berbeda")

        # Check Jetty K3 percentage constraints
        if 'K3' in self.active_jetties:
            target_outloading_K3 = sum(self.outloading_target[o] for o in self.active_jetties['K3'])
            hopper_K3 = sum(prob.variablesDict()[f"flow_{h}_K3_{o}"].varValue 
                            for h in active_hoppers for o in self.active_jetties['K3'])
            if hopper_K3 < 0.6 * target_outloading_K3:
                violated_constraints.append(f"Aliran Hopper ke Jetty K3 di bawah 60% dari target ({hopper_K3:.2f} < {0.6 * target_outloading_K3:.2f})")

        return violated_constraints

    def run_optimization(self, active_hoppers, active_reclaimers, active_outloadings):
            # Initialize problem
            prob = pulp.LpProblem("Network_Flow_Optimization", pulp.LpMaximize)

            # Define variables
            jetties = {'K1': ['L4', 'L6', 'L26'], 'K3': ['L20', 'L9', 'L29']}
            self.active_jetties = {j: [o for o in ol if o in active_outloadings] for j, ol in jetties.items()}
            self.active_jetties = {j: ol for j, ol in self.active_jetties.items() if ol}

            # Create decision variables
            flow = pulp.LpVariable.dicts("flow",
                                        ((h, j, o) for h in active_hoppers for j in self.active_jetties for o in self.active_jetties[j]),
                                        lowBound=0,
                                        cat='Continuous')

            reclaim_flow = pulp.LpVariable.dicts("reclaim_flow",
                                                ((r, j, o) for r in active_reclaimers for j in self.active_jetties for o in self.active_jetties[j]),
                                                lowBound=0,
                                                cat='Continuous')

            hopper_use = pulp.LpVariable.dicts("hopper_use",
                                            ((h, o) for h in active_hoppers for o in active_outloadings),
                                            cat='Binary')

            reclaimer_use = pulp.LpVariable.dicts("reclaimer_use",
                                                ((r, o) for r in active_reclaimers for o in active_outloadings),
                                                cat='Binary')
            
            # Add new variables for the constraint H5 & L8 to L9
            h5_to_l9 = pulp.LpVariable("h5_to_l9", cat='Binary')
            l8_to_l9 = pulp.LpVariable("l8_to_l9", cat='Binary')

            # Objective function
            prob += pulp.lpSum(flow[h,j,o] for h in active_hoppers for j in self.active_jetties for o in self.active_jetties[j]) + \
                    pulp.lpSum(reclaim_flow[r,j,o] for r in active_reclaimers for j in self.active_jetties for o in self.active_jetties[j])

            # Constraints
            # Hopper capacity constraints
            for h in active_hoppers:
                prob += pulp.lpSum(flow[h,j,o] for j in self.active_jetties for o in self.active_jetties[j]) <= self.hopper_capacity[h]

            # Reclaimer capacity constraints
            for r in active_reclaimers:
                prob += pulp.lpSum(reclaim_flow[r,j,o] for j in self.active_jetties for o in self.active_jetties[j]) <= self.reclaimer_capacity[r]

            # Hopper flow constraints
            allowed_flows = {
                'H1': ['L4'],
                'H2': ['L4', 'L26'],
                'H3': ['L20'],
                'H4': ['L20'],
                'H5': ['L9', 'L6'],
                'H6': ['L6', 'L26'],
                'H7': ['L29', 'L26']
            }

            for h in active_hoppers:
                for j in self.active_jetties:
                    for o in self.active_jetties[j]:
                        if o not in allowed_flows[h] or o not in active_outloadings:
                            prob += flow[h,j,o] == 0

            # Reclaimer flow constraints
            allowed_reclaim_flows = {
                'L3': ['L4', 'L6'],
                'L1': ['L4'],
                'L2': ['L26'],
                'L8': ['L9'],
                'L21': ['L29', 'L26'],
                'L16': ['L29', 'L26'],
                'L17': ['L20'],
                'L18': ['L20'],
                'L19': ['L20']
            }

            for r in active_reclaimers:
                for j in self.active_jetties:
                    for o in self.active_jetties[j]:
                        if o not in allowed_reclaim_flows[r] or o not in active_outloadings:
                            prob += reclaim_flow[r,j,o] == 0
                        else:
                            # Add this constraint to ensure flow is only allowed for permitted combinations
                            prob += reclaim_flow[r,j,o] <= self.reclaimer_capacity[r] * reclaimer_use[r,o]

            # Ensure reclaimer is only used for allowed outloadings
            for r in active_reclaimers:
                for o in active_outloadings:
                    if o not in allowed_reclaim_flows[r]:
                        prob += reclaimer_use[r,o] == 0

            # Outloading target constraints
            for o in active_outloadings:
                prob += pulp.lpSum(flow[h,j,o] for h in active_hoppers for j in self.active_jetties if o in self.active_jetties[j]) + \
                        pulp.lpSum(reclaim_flow[r,j,o] for r in active_reclaimers for j in self.active_jetties if o in self.active_jetties[j]) >= 0.8 * self.outloading_target[o]
                prob += pulp.lpSum(flow[h,j,o] for h in active_hoppers for j in self.active_jetties if o in self.active_jetties[j]) + \
                        pulp.lpSum(reclaim_flow[r,j,o] for r in active_reclaimers for j in self.active_jetties if o in self.active_jetties[j]) <= 1.7 * self.outloading_target[o]

            # Hopper usage constraints
            for h in active_hoppers:
                # Ensure each hopper is used exactly once
                prob += pulp.lpSum(hopper_use[h,o] for o in active_outloadings) == 1

                # Link flow to usage and ensure at least 10% capacity utilization when used
                for o in active_outloadings:
                    prob += pulp.lpSum(flow[h,j,o] for j in self.active_jetties if o in self.active_jetties[j]) >= 0.9 * self.hopper_capacity[h] * hopper_use[h,o]
                    prob += pulp.lpSum(flow[h,j,o] for j in self.active_jetties if o in self.active_jetties[j]) <= 1.2 * self.hopper_capacity[h] * hopper_use[h,o]

            # Add the new constraint for H5 and L8 to L9
            if 'H5' in active_hoppers and 'L8' in active_reclaimers and 'L9' in active_outloadings:
                # Link h5_to_l9 to the actual flow
                for j in self.active_jetties:
                    if 'L9' in self.active_jetties[j]:
                        prob += flow['H5', j, 'L9'] <= self.hopper_capacity['H5'] * h5_to_l9
                        prob += flow['H5', j, 'L9'] >= h5_to_l9  # Ensure h5_to_l9 is 1 if there's any flow

                # Link l8_to_l9 to the actual flow
                for j in self.active_jetties:
                    if 'L9' in self.active_jetties[j]:
                        prob += reclaim_flow['L8', j, 'L9'] <= self.reclaimer_capacity['L8'] * l8_to_l9
                        prob += reclaim_flow['L8', j, 'L9'] >= l8_to_l9  # Ensure l8_to_l9 is 1 if there's any flow

                # Add the constraint: H5 and L8 cannot both send to L9 simultaneously
                prob += h5_to_l9 + l8_to_l9 <= 1

            # Ensure flow is zero if hopper is not used
            for h in active_hoppers:
                for j in self.active_jetties:
                    for o in self.active_jetties[j]:
                        prob += flow[h,j,o] <= self.hopper_capacity[h] * hopper_use[h,o]

            # Reclaimer usage constraints
            for r in active_reclaimers:
                # Ensure each reclaimer is used at most once
                prob += pulp.lpSum(reclaimer_use[r,o] for o in active_outloadings) <= 1

                # Link flow to usage
                for o in active_outloadings:
                    prob += pulp.lpSum(reclaim_flow[r,j,o] for j in self.active_jetties if o in self.active_jetties[j]) <= self.reclaimer_capacity[r] * reclaimer_use[r,o]

                # Ensure flow is zero if reclaimer is not used
                for j in self.active_jetties:
                    for o in self.active_jetties[j]:
                        prob += reclaim_flow[r,j,o] <= self.reclaimer_capacity[r] * reclaimer_use[r,o]
                
            # Additional constraint L16 & L21
            if 'L16' in active_reclaimers and 'L21' in active_reclaimers:
                # L16 and L21 can be used simultaneously for the same outloading
                for o in ['L29', 'L26']:
                    if o in active_outloadings:
                        # No restriction for simultaneous use on the same outloading
                        pass

                # L16 and L21 cannot be used simultaneously for different outloadings
                if 'L29' in active_outloadings and 'L26' in active_outloadings:
                    prob += reclaimer_use['L16','L29'] + reclaimer_use['L21','L26'] <= 1
                    prob += reclaimer_use['L16','L26'] + reclaimer_use['L21','L29'] <= 1

                # Ensure that at most one of L16 or L21 is used if outloadings are different
                # Create a new binary variable for each outloading
                min_use = pulp.LpVariable.dicts("min_use", (o for o in active_outloadings), cat='Binary')
                
                for o in active_outloadings:
                    # Ensure min_use[o] is less than or equal to both reclaimer_use['L16',o] and reclaimer_use['L21',o]
                    prob += min_use[o] <= reclaimer_use['L16',o]
                    prob += min_use[o] <= reclaimer_use['L21',o]
                    
                    # Ensure min_use[o] is greater than or equal to reclaimer_use['L16',o] + reclaimer_use['L21',o] - 1
                    # This constraint, combined with the two above, ensures min_use[o] = min(reclaimer_use['L16',o], reclaimer_use['L21',o])
                    prob += min_use[o] >= reclaimer_use['L16',o] + reclaimer_use['L21',o] - 1

                # Add the constraint using the new min_use variables
                prob += pulp.lpSum(reclaimer_use['L16',o] for o in active_outloadings) + \
                        pulp.lpSum(reclaimer_use['L21',o] for o in active_outloadings) <= 1 + \
                        pulp.lpSum(min_use[o] for o in active_outloadings)

            # Percentage constraints for Hopper and Reclaimer on Jetty K1
            if 'K1' in self.active_jetties:
                target_outloading_K1 = sum(self.outloading_target[o] for o in self.active_jetties['K1'])
                hopper_K1 = pulp.lpSum(flow[h,'K1',o] for h in active_hoppers for o in self.active_jetties['K1'])
                reclaimer_K1 = pulp.lpSum(reclaim_flow[r,'K1',o] for r in active_reclaimers for o in self.active_jetties['K1'])

                prob += hopper_K1 >= 0 * target_outloading_K1
                prob += hopper_K1 <= 1.0 * target_outloading_K1
                prob += reclaimer_K1 >= 0 * target_outloading_K1
                prob += reclaimer_K1 <= 1.0 * target_outloading_K1

            # Percentage constraints for Hopper and Reclaimer on Jetty K3
            if 'K3' in self.active_jetties:
                target_outloading_K3 = sum(self.outloading_target[o] for o in self.active_jetties['K3'])
                hopper_K3 = pulp.lpSum(flow[h,'K3',o] for h in active_hoppers for o in self.active_jetties['K3'])
                reclaimer_K3 = pulp.lpSum(reclaim_flow[r,'K3',o] for r in active_reclaimers for o in self.active_jetties['K3'])

                prob += hopper_K3 >= 0.6 * target_outloading_K3
                prob += hopper_K3 <= 1.0 * target_outloading_K3
                prob += reclaimer_K3 >= 0 * target_outloading_K3
                prob += reclaimer_K3 <= 1.0 * target_outloading_K3

            # Solve the problem
            prob.solve()
            
            # Get the status
            status = pulp.LpStatus[prob.status]

            # Format and return results
            result = f"Status: {pulp.LpStatus[prob.status]}\n"
            result += "-----" * 30 + "\n"
        
            for j, outloadings_j in self.active_jetties.items():
                result += f"\nRingkasan Jetty {j}:\n"
        
                # Calculate total target outloading for the jetty
                target_outloading_j = sum(self.outloading_target[o] for o in outloadings_j)
        
                # Calculate Hopper summary
                hopper_total = sum(flow[h,j,o].value() for h in active_hoppers for o in outloadings_j)
                reclaimer_total = sum(reclaim_flow[r,j,o].value() for r in active_reclaimers for o in outloadings_j)
                total_tonnage = hopper_total + reclaimer_total
                hopper_percentage = (hopper_total / total_tonnage) * 100 if total_tonnage > 0 else 0
                result += f"\nTotal tonase Hopper ke Jetty {j}: {int(hopper_total)} | Persentase Hopper terhadap Reclaimer: {hopper_percentage:.0f}%\n"
        
                hopper_flows = []
                for h in active_hoppers:
                    for o in outloadings_j:
                        if flow[h,j,o].value() > 0:
                            hopper_flows.append((h, o, flow[h,j,o].value()))
        
                for i, (h, o, f) in enumerate(sorted(hopper_flows, key=lambda x: x[2], reverse=True), 1):
                    result += f"{i}. {h} ke {o} | {int(f)}\n"
        
                # Calculate Reclaimer summary
                reclaimer_percentage = (reclaimer_total / total_tonnage) * 100 if total_tonnage > 0 else 0
                result += f"\nTotal tonase Reclaimer ke Jetty {j}: {int(reclaimer_total)} | Persentase Reclaimer terhadap Hopper: {reclaimer_percentage:.0f}%\n"
        
                reclaimer_flows = []
                for r in active_reclaimers:
                    for o in outloadings_j:
                        if reclaim_flow[r,j,o].value() > 0:
                            reclaimer_flows.append((r, o, reclaim_flow[r,j,o].value()))
        
                for i, (r, o, f) in enumerate(sorted(reclaimer_flows, key=lambda x: x[2], reverse=True), 1):
                    result += f"{i}. {r} ke {o} | {int(f)}\n"
        
                # Print total tonnage for each outloading line
                result += "\n"
                total_jetty_tonnage = sum(sum(flow[h,j,o].value() for h in active_hoppers) + sum(reclaim_flow[r,j,o].value() for r in active_reclaimers)
                            for o in outloadings_j)
                result += f"Total tonase untuk Jetty {j} = {int(total_jetty_tonnage)}/jam\n"
                result += "-----" * 30 + "\n"
        
            result += "\nRingkasan Keseluruhan:\n"
            for o in active_outloadings:
                total_tonnage = sum(flow[h,j,o].value() for h in active_hoppers for j in self.active_jetties if o in self.active_jetties[j]) + \
                                sum(reclaim_flow[r,j,o].value() for r in active_reclaimers for j in self.active_jetties if o in self.active_jetties[j])
                result += f"{o} = {int(total_tonnage)}/jam\n"
        
            return prob, result, status

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set the app icon for the entire application
    icon_path = get_icon_path()
    if icon_path:
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    
    window = OptimizationApp()
    window.show()
    sys.exit(app.exec_())