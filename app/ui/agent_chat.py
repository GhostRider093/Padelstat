"""
Interface de chat agent avec Ollama
Permet d'interagir avec l'IA pour obtenir des analyses, générer des rapports, etc.
"""

import os
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QLineEdit, QLabel, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor, QPalette
import requests
import json
import webbrowser


class AgentThread(QThread):
    """Thread pour les requêtes à l'agent Ollama"""
    response_received = pyqtSignal(str)
    action_triggered = pyqtSignal(str, dict)  # action_type, params
    error_occurred = pyqtSignal(str)
    
    def __init__(self, message, context=None):
        super().__init__()
        self.message = message
        self.context = context or {}
        self.model = "llama3.2:3b"
        
    def run(self):
        try:
            # Analyser la demande pour détecter des actions
            action_result = self._detect_and_execute_action()
            if action_result:
                return
            
            # Sinon, conversation normale
            system_prompt = self._build_system_prompt()
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\nUtilisateur: {self.message}\n\nAssistant:",
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "Désolé, je n'ai pas pu générer de réponse.")
                self.response_received.emit(answer)
            else:
                self.error_occurred.emit(f"Erreur {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.error_occurred.emit("⏱️ Timeout - L'IA a mis trop de temps à répondre")
        except Exception as e:
            self.error_occurred.emit(f"❌ Erreur: {str(e)}")
    
    def _detect_and_execute_action(self):
        """Détecte et exécute des actions basées sur le message"""
        message_lower = self.message.lower()
        
        # Génération de rapport HTML
        if any(word in message_lower for word in ["rapport", "html", "ouvre", "génère", "affiche"]):
            if any(word in message_lower for word in ["rapport", "html"]):
                self.action_triggered.emit("generate_report", {})
                self.response_received.emit("✅ Je génère le rapport HTML live pour vous...")
                return True
        
        # Analyse du match
        if any(word in message_lower for word in ["analyse", "résumé", "match", "stats"]):
            self.action_triggered.emit("analyze_match", {})
            return True
        
        # Conseils tactiques
        if any(word in message_lower for word in ["conseil", "améliorer", "stratégie", "tactique"]):
            self.action_triggered.emit("tactical_advice", {})
            return True
        
        return False
    
    def _build_system_prompt(self):
        """Construit le prompt système avec contexte"""
        prompt = """Tu es un assistant expert en padel intégré dans l'application Padel Stat.

Tu peux aider l'utilisateur à:
- Analyser les statistiques de match
- Générer des rapports HTML (dis "rapport HTML" ou "génère le rapport")
- Donner des conseils tactiques
- Expliquer les données
- Répondre aux questions sur le padel

Contexte actuel:
"""
        
        if self.context.get("match_loaded"):
            prompt += f"\n- Match en cours: {self.context.get('match_name', 'Sans nom')}"
            prompt += f"\n- Nombre de points: {self.context.get('num_points', 0)}"
            
            if self.context.get("score"):
                prompt += f"\n- Score: {self.context['score']}"
        else:
            prompt += "\n- Aucun match chargé actuellement"
        
        prompt += "\n\nRéponds de manière concise et utile en français. Utilise des emojis pour rendre tes réponses plus vivantes 🎾"
        
        return prompt


class MessageBubble(QFrame):
    """Bulle de message stylisée"""
    def __init__(self, text, is_user=True):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout()
        
        # Label du texte
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        
        font = QFont()
        font.setPointSize(10)
        label.setFont(font)
        
        layout.addWidget(label)
        self.setLayout(layout)
        
        # Style selon l'expéditeur
        if is_user:
            self.setStyleSheet("""
                QFrame {
                    background-color: #0084ff;
                    color: white;
                    border-radius: 15px;
                    padding: 10px 15px;
                    margin: 5px 50px 5px 5px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #e4e6eb;
                    color: #050505;
                    border-radius: 15px;
                    padding: 10px 15px;
                    margin: 5px 5px 5px 50px;
                }
            """)


class AgentChatWidget(QWidget):
    """Widget de chat avec l'agent IA"""
    
    # Signal pour demander des actions à l'application principale
    action_requested = pyqtSignal(str, dict)  # action_type, params
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.agent_thread = None
        self.context = {}
        self.init_ui()
        
    def init_ui(self):
        """Initialize l'interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("🤖 Agent Padel IA")
        header.setStyleSheet("""
            QLabel {
                background-color: #0084ff;
                color: white;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(header)
        
        # Zone de messages (scroll area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout()
        self.messages_layout.addStretch()
        self.messages_widget.setLayout(self.messages_layout)
        
        scroll.setWidget(self.messages_widget)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
        """)
        layout.addWidget(scroll, 1)
        
        # Zone de suggestions
        suggestions_layout = QHBoxLayout()
        suggestions = [
            "📊 Analyse le match",
            "📄 Génère le rapport",
            "💡 Donne des conseils",
            "📈 Stats détaillées"
        ]
        
        for suggestion in suggestions:
            btn = QPushButton(suggestion)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f2f5;
                    border: 1px solid #ddd;
                    border-radius: 15px;
                    padding: 8px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #e4e6eb;
                }
            """)
            btn.clicked.connect(lambda checked, s=suggestion: self.send_suggestion(s))
            suggestions_layout.addWidget(btn)
        
        layout.addLayout(suggestions_layout)
        
        # Zone de saisie
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Posez une question ou demandez une action...")
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ddd;
                border-radius: 20px;
                padding: 10px 15px;
                font-size: 12px;
                background-color: #f0f2f5;
            }
            QLineEdit:focus {
                border-color: #0084ff;
                background-color: white;
            }
        """)
        
        self.send_btn = QPushButton("Envoyer 🚀")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0084ff;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0073e6;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        
        # Message de bienvenue
        self.add_agent_message(
            "👋 Salut ! Je suis ton assistant padel IA.\n\n"
            "Je peux t'aider à:\n"
            "• 📊 Analyser tes statistiques de match\n"
            "• 📄 Générer des rapports HTML\n"
            "• 💡 Donner des conseils tactiques\n"
            "• 📈 Expliquer les données\n\n"
            "Pose-moi une question ou clique sur une suggestion !"
        )
    
    def send_suggestion(self, suggestion):
        """Envoie une suggestion prédéfinie"""
        # Retirer l'emoji du début
        text = suggestion.split(' ', 1)[1] if ' ' in suggestion else suggestion
        self.input_field.setText(text)
        self.send_message()
    
    def send_message(self):
        """Envoie un message à l'agent"""
        message = self.input_field.text().strip()
        if not message:
            return
        
        # Afficher le message utilisateur
        self.add_user_message(message)
        self.input_field.clear()
        
        # Désactiver l'input pendant le traitement
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # Lancer le thread agent
        self.agent_thread = AgentThread(message, self.context)
        self.agent_thread.response_received.connect(self.on_response)
        self.agent_thread.action_triggered.connect(self.on_action)
        self.agent_thread.error_occurred.connect(self.on_error)
        self.agent_thread.finished.connect(self.on_thread_finished)
        self.agent_thread.start()
    
    def add_user_message(self, text):
        """Ajoute un message utilisateur"""
        bubble = MessageBubble(text, is_user=True)
        # Insérer avant le stretch
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        
        # Scroll vers le bas
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def add_agent_message(self, text):
        """Ajoute un message agent"""
        bubble = MessageBubble(text, is_user=False)
        # Insérer avant le stretch
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        
        # Scroll vers le bas
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Scroll vers le bas de la conversation"""
        scroll_area = self.messages_widget.parent()
        if isinstance(scroll_area, QScrollArea):
            scrollbar = scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def on_response(self, response):
        """Gère la réponse de l'agent"""
        self.add_agent_message(response)
    
    def on_action(self, action_type, params):
        """Gère une action déclenchée par l'agent"""
        # Émettre le signal vers l'application principale
        self.action_requested.emit(action_type, params)
    
    def on_error(self, error_msg):
        """Gère une erreur"""
        self.add_agent_message(f"❌ {error_msg}")
    
    def on_thread_finished(self):
        """Réactive l'interface quand le thread se termine"""
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
    
    def update_context(self, match_data=None, stats=None):
        """Met à jour le contexte de l'agent"""
        if match_data:
            self.context["match_loaded"] = True
            self.context["match_name"] = match_data.get("name", "Match sans nom")
            self.context["num_points"] = len(match_data.get("points", []))
            self.context["score"] = match_data.get("score", "")
            self.context["teams"] = match_data.get("teams", {})
        
        if stats:
            self.context["stats"] = stats
    
    def clear_context(self):
        """Efface le contexte"""
        self.context = {}
