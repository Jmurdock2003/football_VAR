# ThrowIn_Detector.py
from event_detector.RuleKnowledgeGraph import RuleKnowledgeGraph

class ThrowInDetector:
    def __init__(self, field_width=1280):
        """
        field_width: Pitch width in pixels.
        """
        self.field_width = field_width
        self.kg = RuleKnowledgeGraph()
        self.rule = self.kg.get_rule("Throw-In Rule")

    def check_throw_in(self, ball_position, last_team_touch):
        """
        ball_position: (x, y)
        last_team_touch: team number (1 or 2)

        Returns team number awarded throw-in, or None
        """
        x, y = ball_position

        if x < 0:
            return 2 if last_team_touch == 1 else 1  # Ball out left side
        elif x > self.field_width:
            return 2 if last_team_touch == 1 else 1  # Ball out right side
        else:
            return None
