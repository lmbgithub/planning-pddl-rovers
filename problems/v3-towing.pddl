(define (problem roverprob1234p4)
	(:domain Rover-batteryp4)
	(:objects
		general - Lander
		colour high_res low_res - Mode
		rover0 rover1 - rover
		rover0store rover1store - Store
		waypoint0 waypoint1 waypoint2 waypoint3 - Waypoint
		camera0 camera1 - Camera
		objective0 objective1 - Objective
		b0 b1 b2 b3 b4 b5 - Blevel
		bat0 bat1 - Battery
	)
	(:init
		; rovers
		(use_wheels rover0)
		(use_legs rover1)
		(at rover0 waypoint3)
		(at rover1 waypoint3)
		(available rover0)
		(available rover1)
		(store_of rover0store rover0)
		(store_of rover1store rover1)
		(empty rover0store)
		(empty rover1store)
		(equipped_for_soil_analysis rover0)
		(equipped_for_rock_analysis rover1)
		(equipped_for_imaging rover0)
		(equipped_for_imaging rover1)
		(on_board camera0 rover0)
		(on_board camera1 rover1)
		(calibration_target camera0 objective1)
		(calibration_target camera1 objective0)
		(supports camera0 colour)
		(supports camera0 high_res)
		(supports camera1 colour)
		(supports camera1 high_res)
		(battery_installed rover0 bat0 b4 b4)
		(battery_installed rover1 bat1 b4 b4)

		(can_traverse rover0 waypoint3 waypoint0)
		(can_traverse rover0 waypoint0 waypoint3)
		(can_traverse rover0 waypoint0 waypoint1)
		(can_traverse rover0 waypoint1 waypoint0)
		(can_traverse rover0 waypoint1 waypoint2)
		(can_traverse rover0 waypoint2 waypoint1)

		(can_traverse rover1 waypoint3 waypoint0)
		(can_traverse rover1 waypoint0 waypoint3)
		(can_traverse rover1 waypoint0 waypoint1)
		(can_traverse rover1 waypoint1 waypoint0)
		(can_traverse rover1 waypoint1 waypoint2)
		(can_traverse rover1 waypoint2 waypoint1)

		; inclinacion y terreno (definir para todos los caminos)
		(is_clean waypoint0 waypoint1)
		(is_clean waypoint1 waypoint0)
		(is_flat waypoint0 waypoint1)
		(is_flat waypoint1 waypoint0)

		; waypoint0 <-> waypoint3
		(is_road_up waypoint3 waypoint0)
		(is_road_down waypoint0 waypoint3)

		; waypoint1 <-> waypoint2
		(is_road_down waypoint1 waypoint2)
		(is_road_up waypoint2 waypoint1)

		; waypoint1 <-> waypoint3
		(is_road_up waypoint3 waypoint1)
		(is_road_down waypoint1 waypoint3)

		; waypoint2 <-> waypoint3
		(is_road_up waypoint3 waypoint2)
		(is_road_down waypoint2 waypoint3)

		(visible waypoint1 waypoint0)
		(visible waypoint0 waypoint1)
		(visible waypoint2 waypoint0)
		(visible waypoint0 waypoint2)
		(visible waypoint2 waypoint1)
		(visible waypoint1 waypoint2)
		(visible waypoint3 waypoint0)
		(visible waypoint0 waypoint3)
		(visible waypoint3 waypoint1)
		(visible waypoint1 waypoint3)
		(visible waypoint3 waypoint2)
		(visible waypoint2 waypoint3)
		(at_soil_sample waypoint0)
		(at_rock_sample waypoint1)
		(at_soil_sample waypoint2)
		(at_rock_sample waypoint2)
		(at_soil_sample waypoint3)
		(at_rock_sample waypoint3)
		(at_lander general waypoint0)
		(channel_free general)
		; Niveles de bateria
		(lower b0 b1)
		(lower b1 b2)
		(lower b2 b3)
		(lower b3 b4)
		(lower b4 b5)
		; Visibilidad de objetivos
		(visible_from objective0 waypoint0)
		(visible_from objective0 waypoint1)
		(visible_from objective0 waypoint2)
		(visible_from objective0 waypoint3)
		(visible_from objective1 waypoint0)
		(visible_from objective1 waypoint1)
		(visible_from objective1 waypoint2)
		(visible_from objective1 waypoint3)
	)

	(:goal
		(and
			(at rover0 waypoint2)
			(at rover1 waypoint2)
			(communicated_soil_data waypoint2)
			(communicated_rock_data waypoint3)
			(communicated_image_data objective1 high_res)
			(communicated_image_data objective0 colour)
		)
	)
)