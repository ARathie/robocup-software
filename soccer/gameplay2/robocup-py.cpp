#include "robocup-py.hpp"
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>

using namespace boost::python;

#include <Geometry2d/Point.hpp>
#include <Robot.hpp>
#include <SystemState.hpp>
#include <protobuf/LogFrame.pb.h>


/**
 * The code in this block wraps up c++ classes and makes them
 * accessible to python in the 'robocup' module.
 */
BOOST_PYTHON_MODULE(robocup)
{
	class_<Geometry2d::Point>("Point", init<float, float>())
		.def_readwrite("x", &Geometry2d::Point::x)
		.def_readwrite("y", &Geometry2d::Point::y)
	;

	//	TODO: add the rest of GameState stuff here
	//		I'm holding off for now because GameState needs some attention on the C++
	//		side of things before we spread its shortcomings into the python world too...
	class_<GameState>("GameState")
		.def_readonly("our_score", &GameState::ourScore)
		.def_readonly("their_score", &GameState::theirScore)
	;

	class_<Robot>("Robot", init<int, bool>())
		.def("shell_id", &Robot::shell)
		.def("is_ours", &Robot::self)
		.def_readwrite("pos", &Robot::pos)
		.def_readwrite("vel", &Robot::vel)
		.def_readwrite("angle", &Robot::angle)
		.def_readwrite("angle_vel", &Robot::angleVel)
	;

	class_<OurRobot, bases<Robot> >("OurRobot", init<int, SystemState*>());

	class_<OpponentRobot, bases<Robot> >("OpponentRobot", init<int>());

	class_<Ball>("Ball", init<>())
		.def_readonly("pos", &Ball::pos)
		.def_readonly("vel", &Ball::vel)
	;

	class_<std::vector<OurRobot *> >("OurRobotVector")
		.def(vector_indexing_suite<std::vector<OurRobot> >())
	;

	class_<SystemState>("SystemState")
		.def_readonly("our_robots", &SystemState::self)
		.def_readonly("their_robots", &SystemState::opp)
		.def_readonly("ball", &SystemState::ball)
		.def_readonly("game_state", &SystemState::gameState)
		.def_readonly("timestamp", &SystemState::timestamp)

		//	debug drawing methods
		.def("draw_circle", &SystemState::drawCircle)
		.def("draw_path", &SystemState::drawPath)
		.def("draw_text", &SystemState::drawText)
		.def("draw_obstacle", &SystemState::drawObstacle)
		.def("draw_obstacles", &SystemState::drawObstacles)
	;
}