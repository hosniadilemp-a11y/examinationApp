import json
from typing import Dict, Set, Any
from fastapi import WebSocket

class WebSocketConnectionManager:
    """
    Gestionnaire central des connexions WebSocket pour la télémétrie en direct.
    Gère les canaux d'écoute des enseignants et les flux d'événements des postes étudiants.
    """
    def __init__(self):
        # session_id -> Set[WebSocket] des surveillants/enseignants
        self.teacher_connections: Dict[str, Set[WebSocket]] = {}
        # session_id -> {student_id: WebSocket}
        self.student_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect_teacher(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.teacher_connections:
            self.teacher_connections[session_id] = set()
        self.teacher_connections[session_id].add(websocket)

    def disconnect_teacher(self, session_id: str, websocket: WebSocket):
        if session_id in self.teacher_connections:
            self.teacher_connections[session_id].discard(websocket)
            if not self.teacher_connections[session_id]:
                del self.teacher_connections[session_id]

    async def connect_student(self, session_id: str, student_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.student_connections:
            self.student_connections[session_id] = {}
        self.student_connections[session_id][student_id] = websocket
        
        # Notifier immédiatement les surveillants de la connexion de cet étudiant
        await self.broadcast_to_teachers(session_id, {
            "type": "STUDENT_CONNECTED",
            "student_id": student_id,
            "timestamp": None
        })

    async def disconnect_student(self, session_id: str, student_id: str):
        if session_id in self.student_connections and student_id in self.student_connections[session_id]:
            del self.student_connections[session_id][student_id]
            if not self.student_connections[session_id]:
                del self.student_connections[session_id]
                
        # Notifier les surveillants de la déconnexion
        await self.broadcast_to_teachers(session_id, {
            "type": "STUDENT_DISCONNECTED",
            "student_id": student_id
        })

    async def broadcast_to_teachers(self, session_id: str, message: Dict[str, Any]):
        """Diffuse un événement en direct à tous les enseignants surveillant la salle."""
        if session_id not in self.teacher_connections:
            return
            
        payload = json.dumps(message)
        dead_connections = set()
        for ws in self.teacher_connections[session_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead_connections.add(ws)
                
        for dead_ws in dead_connections:
            self.teacher_connections[session_id].discard(dead_ws)

    async def send_to_student(self, session_id: str, student_id: str, message: Dict[str, Any]):
        """Envoie un ordre spécifique à un poste étudiant (ex: déblocage, ajout de temps)."""
        if session_id in self.student_connections and student_id in self.student_connections[session_id]:
            ws = self.student_connections[session_id][student_id]
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass

    async def broadcast_to_all_students(self, session_id: str, message: Dict[str, Any]):
        """Envoie un ordre à tous les étudiants de la salle (ex: Lancement groupé de l'épreuve)."""
        if session_id not in self.student_connections:
            return
            
        payload = json.dumps(message)
        for student_id, ws in list(self.student_connections[session_id].items()):
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    def is_student_connected(self, session_id: str, student_id: str) -> bool:
        """Indique si un étudiant est actuellement connecté en WebSocket actif sur la session."""
        return session_id in self.student_connections and student_id in self.student_connections[session_id]

ws_manager = WebSocketConnectionManager()
