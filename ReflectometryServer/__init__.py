"""
Classes used by configuration for easy import
"""
import six


if six.PY2:
    print("Reflectometry IOC can not be run in python 2!!")
else:
    from ReflectometryServer.beamline import Beamline, BeamlineMode
    from ReflectometryServer.beamline_constant import BeamlineConstant
    from ReflectometryServer.components import Component, ReflectingComponent, ThetaComponent, TiltingComponent, \
        BenchComponent, BenchSetup
    from ReflectometryServer.engineering_corrections import ConstantCorrection, UserFunctionCorrection, \
        InterpolateGridDataCorrection, SymmetricEngineeringCorrection, NoCorrection, EngineeringCorrection, \
        GridDataFileReader, InterpolateGridDataCorrectionFromProvider, COLUMN_NAME_FOR_DRIVER_SETPOINT
    from ReflectometryServer.footprint_manager import FootprintSetup, BaseFootprintSetup
    from ReflectometryServer.geometry import PositionAndAngle, Position, ChangeAxis
    from ReflectometryServer.ioc_driver import IocDriver
    from ReflectometryServer.out_of_beam import OutOfBeamPosition
    from ReflectometryServer.parameters import InBeamParameter, AxisParameter, DirectParameter, \
        SlitGapParameter
    from ReflectometryServer.pv_wrapper import MotorPVWrapper, JawsCentrePVWrapper, JawsGapPVWrapper, PVWrapper
    from ReflectometryServer.config_helper import ConfigHelper, get_configured_beamline, add_constant, add_component, \
        add_parameter, add_mode, add_driver, add_slit_parameters, add_beam_start, add_footprint_setup, \
        add_component_marker, add_driver_marker, add_parameter_marker
