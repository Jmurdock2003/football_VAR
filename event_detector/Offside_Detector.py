from event_detector.RuleKnowledgeGraph import RuleKnowledgeGraph
from utils import measure_distance

class OffsideDetector:
    def __init__(self, attack_direction="right", kick_threshold=5):
        self.attack_direction = attack_direction
        self.kick_threshold = kick_threshold
        self.last_ball_position = None
        self.kg = RuleKnowledgeGraph()
        self.rule = self.kg.get_rule("Offside Rule")

    def update(self, current_ball_position):
        if self.last_ball_position is None:
            self.last_ball_position = current_ball_position
            return False

        dx = current_ball_position[0] - self.last_ball_position[0]
        dy = current_ball_position[1] - self.last_ball_position[1]
        velocity = (dx**2 + dy**2)**0.5

        self.last_ball_position = current_ball_position
        return velocity > self.kick_threshold

    def check_offside(self, team_players, opponent_players, ball_position):
        if not team_players or len(opponent_players) < 2:
            return None

        # Sort opponents to find second-last defender
        sorted_defenders = sorted(opponent_players, key=lambda p: p[1][0], reverse=(self.attack_direction == "left"))
        second_last_def_x = sorted_defenders[1][1][0]
        ball_x = ball_position[0]

        # Find nearest attacker (likely receiver)
        nearest_player = None
        min_dist = float('inf')
        for player_id, (x, y) in team_players:
            dist = measure_distance((x, y), ball_position)
            if dist < min_dist:
                nearest_player = (player_id, x)
                min_dist = dist

        if not nearest_player:
            return None

        player_id, player_x = nearest_player

        if self.attack_direction == "right":
            if player_x > ball_x and player_x > second_last_def_x:
                return player_id
        else:
            if player_x < ball_x and player_x < second_last_def_x:
                return player_id

        return None
