from utils import read_video, save_video
from trackers import Tracker
import cv2
import numpy as np
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from camera_movement_estimator import CameraMovementEstimator
from view_transformer import ViewTransformer
from speed_and_distance_estimator import SpeedAndDistance_Estimator
from event_detector.Offside_Detector import OffsideDetector
from event_detector.ThrowIn_Detector import ThrowInDetector
from event_detector.CornerGoal_Detector import CornerGoalDetector
from communication.Speech_Output import SpeechOutput
from utils import measure_distance

# --- Utility: Convert RGB color to color name ---
def rgb_to_color_name(rgb):
    r, g, b = rgb
    if r > 200 and g < 100 and b < 100:
        return "Red Team"
    elif r < 100 and g > 200 and b < 100:
        return "Green Team"
    elif r < 100 and g < 100 and b > 200:
        return "Blue Team"
    elif r > 200 and g > 200 and b < 100:
        return "Yellow Team"
    elif r > 150 and g > 150 and b > 150:
        return "White Team"
    else:
        return "Dark Team"

def main():
    # Read Video
    video_frames = read_video('input_videos/08fd33_4.mp4')

    # Initialize Tracker
    tracker = Tracker('models/best.pt')
    tracks = tracker.get_object_tracks(video_frames, read_from_stub=True, stub_path='stubs/track_stubs.pkl')
    tracker.add_position_to_tracks(tracks)

    # Camera Movement Estimator
    camera_movement_estimator = CameraMovementEstimator(video_frames[0])
    camera_movement_per_frame = camera_movement_estimator.get_camera_movement(video_frames, read_from_stub=True, stub_path='stubs/camera_movement_stub.pkl')
    camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement_per_frame)

    # View Transformer
    view_transformer = ViewTransformer()
    view_transformer.add_transformed_position_to_tracks(tracks)

    # Ball Interpolation Fix
    tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])
    for frame in tracks['ball']:
        if 1 in frame:
            bbox = frame[1]['bbox']
            frame[1]['position'] = (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2))

    # Speed and Distance Estimator
    speed_and_distance_estimator = SpeedAndDistance_Estimator()
    speed_and_distance_estimator.add_speed_and_distance_to_tracks(tracks)

    # Assign Teams
    team_assigner = TeamAssigner()
    team_assigner.assign_team_color(video_frames[0], tracks['players'][0])

    team_names = {
        1: rgb_to_color_name(team_assigner.team_colors[1]),
        2: rgb_to_color_name(team_assigner.team_colors[2])
    }
    print(team_names)

    for frame_num, player_track in enumerate(tracks['players']):
        for player_id, track in player_track.items():
            team = team_assigner.get_player_team(video_frames[frame_num], track['bbox'], player_id)
            tracks['players'][frame_num][player_id]['team'] = team
            tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_colors[team]

    # Ball Assignment and Last Touch Tracking
    player_assigner = PlayerBallAssigner()
    team_ball_control = []
    last_team_touch = []

    for frame_num, player_track in enumerate(tracks['players']):
        ball_bbox = tracks['ball'][frame_num][1]['bbox']
        assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

        if assigned_player != -1:
            tracks['players'][frame_num][assigned_player]['has_ball'] = True
            team = tracks['players'][frame_num][assigned_player]['team']
            team_ball_control.append(team)
            last_team_touch.append(team)
        else:
            if len(last_team_touch) > 0:
                last_team_touch.append(last_team_touch[-1])
                team_ball_control.append(team_ball_control[-1])
            else:
                last_team_touch.append(0)
                team_ball_control.append(0)

    team_ball_control = np.array(team_ball_control)
    last_team_touch = np.array(last_team_touch)

    # Initialize Detectors and TTS
    offside_detector = OffsideDetector()
    throw_in_detector = ThrowInDetector(field_width=1280)
    corner_goal_detector = CornerGoalDetector(field_width=1280)
    tts = SpeechOutput()

    # Cooldown to prevent spamming
    event_cooldown = 0
    cooldown_limit = 60  # frames

    # --- New Smart Attack Direction Detection ---
    total_dx_team1 = 0
    total_dx_team2 = 0
    count_team1 = 0
    count_team2 = 0

    previous_ball_position = None

    for frame_num in range(min(50, len(video_frames))):
        ball_frame_data = tracks['ball'][frame_num]
        if 1 not in ball_frame_data or 'position' not in ball_frame_data[1]:
            continue
        ball_pos = ball_frame_data[1]['position']
        ball_team = team_ball_control[frame_num]

        if previous_ball_position is not None:
            dx = ball_pos[0] - previous_ball_position[0]

            if ball_team == 1:
                total_dx_team1 += dx
                count_team1 += 1
            elif ball_team == 2:
                total_dx_team2 += dx
                count_team2 += 1

        previous_ball_position = ball_pos

    attack_direction_team1 = "right"
    attack_direction_team2 = "left"

    if count_team1 > 0:
        avg_dx_team1 = total_dx_team1 / count_team1
        attack_direction_team1 = "right" if avg_dx_team1 > 0 else "left"

    if count_team2 > 0:
        avg_dx_team2 = total_dx_team2 / count_team2
        attack_direction_team2 = "right" if avg_dx_team2 > 0 else "left"

    print(f"Team 1 attacks {attack_direction_team1}")
    print(f"Team 2 attacks {attack_direction_team2}")

    # Event detection loop
    last_ball_position = None

    for frame_num in range(len(video_frames)):
        if event_cooldown > 0:
            event_cooldown -= 1
            continue

        ball_frame_data = tracks['ball'][frame_num]
        if 1 not in ball_frame_data or 'position' not in ball_frame_data[1]:
            continue
        ball_position = ball_frame_data[1]['position']

        player_frame_data = tracks['players'][frame_num]

        team_players = []
        opponent_players = []

        for player_id, data in player_frame_data.items():
            if data['team'] == 1:
                team_players.append((player_id, data['position']))
            else:
                opponent_players.append((player_id, data['position']))

        current_team = team_ball_control[frame_num]

        if current_team == 1:
            current_attack_direction = attack_direction_team1
        elif current_team == 2:
            current_attack_direction = attack_direction_team2
        else:
            current_attack_direction = "right"

        if last_ball_position is not None:
            dx = ball_position[0] - last_ball_position[0]
            dy = ball_position[1] - last_ball_position[1]
            velocity = (dx**2 + dy**2)**0.5

            ball_moving_forward = (dx > 3) if current_attack_direction == "right" else (dx < -3)
            ball_speed_high = (velocity > 5)

            if ball_moving_forward and ball_speed_high:
                if len(opponent_players) >= 2:
                    sorted_defenders = sorted(opponent_players, key=lambda p: p[1][0], reverse=(current_attack_direction == "left"))
                    second_last_def_x = sorted_defenders[1][1][0]

                    nearest_attacker = None
                    min_dist = float('inf')

                    for player_id, (x, y) in team_players:
                        dist = measure_distance((x, y), ball_position)
                        if dist < min_dist:
                            min_dist = dist
                            nearest_attacker = (player_id, x)

                    if nearest_attacker and min_dist < 50:
                        player_id, player_x = nearest_attacker

                        if (current_attack_direction == "right" and player_x > ball_position[0] and player_x > second_last_def_x) or \
                           (current_attack_direction == "left" and player_x < ball_position[0] and player_x < second_last_def_x):
                            print(f"⚽ Offside detected by Player {player_id}")
                            tts.announce(f"Offside by player {player_id}")
                            event_cooldown = cooldown_limit
                            continue

        last_ball_position = ball_position

        # Throw-in detection
        throw_in_event = throw_in_detector.check_throw_in(ball_position, last_team_touch[frame_num])
        if throw_in_event:
            print(f"🏟️ Throw-in awarded to the {team_names[throw_in_event]}")
            tts.announce(f"Throw-in for the {team_names[throw_in_event]}")
            event_cooldown = cooldown_limit
            continue

        # Corner/Goal kick detection
        corner_goal_event = corner_goal_detector.check_corner_goal(ball_position, last_team_touch[frame_num])
        if corner_goal_event == "corner":
            corner_team = 1 if last_team_touch[frame_num] == 2 else 2
            print(f"🏁 Corner Kick awarded to the {team_names[corner_team]}")
            tts.announce(f"Corner kick for the {team_names[corner_team]}")
            event_cooldown = cooldown_limit
            continue
        elif corner_goal_event == "goal_kick":
            print(f"🧤 Goal Kick awarded to the {team_names[last_team_touch[frame_num]]}")
            tts.announce(f"Goal kick for the {team_names[last_team_touch[frame_num]]}")
            event_cooldown = cooldown_limit
            continue

    # Save Video
    output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)
    output_video_frames = camera_movement_estimator.draw_camera_movement(output_video_frames, camera_movement_per_frame)
    speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)

    save_video(output_video_frames, 'output_videos/output_video.avi')

if __name__ == '__main__':
    main()
