# CornerGoal_Detector.py
from event_detector.RuleKnowledgeGraph import RuleKnowledgeGraph

class CornerGoalDetector:
    def __init__(self, field_width=1280, goal_width=300):
        """
        field_width: Pitch width in pixels (horizontal length).
        goal_width: Width of the goal area (approximate).
        """
        self.field_width = field_width
        self.goal_width = goal_width
        self.kg = RuleKnowledgeGraph()
        self.corner_rule = self.kg.get_rule("Corner Rule")
        self.goal_kick_rule = self.kg.get_rule("Goal Kick Rule")

    def check_corner_goal(self, ball_position, last_team_touch):
        """
        ball_position: (x, y)
        last_team_touch: team number (1 or 2)

        Returns 'corner', 'goal_kick' or None
        """
        x, y = ball_position

        # Assume pitch height is proportional to width
        if y < 0 or y > self.field_width * 0.65:  # 0.65 is rough football field aspect ratio
            if last_team_touch == 1:  # Attacking team last touched
                return "goal_kick"
            elif last_team_touch == 2:  # Defending team last touched
                return "corner"
        
        return None
