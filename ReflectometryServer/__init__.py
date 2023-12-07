"""
Classes used by configuration for easy import
"""
import six
import sys
import os

epics_path = os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir, os.path.pardir)
server_common_path = os.path.abspath(os.path.join(epics_path, "ISIS", "inst_servers", "master"))
sys.path.insert(2, server_common_path)


if six.PY2:
    print("Reflectometry IOC can not be run in python 2!!")
else:
    from ReflectometryServer.beamline import Beamline, BeamlineMode
    from ReflectometryServer.beamline_constant import BeamlineConstant
    from ReflectometryServer.components import Component, ReflectingComponent, ThetaComponent, TiltingComponent, \
        BenchComponent, BenchSetup
    from ReflectometryServer.engineering_corrections import ConstantCorrection, UserFunctionCorrection, \
        InterpolateGridDataCorrection, SymmetricEngineeringCorrection, NoCorrection, EngineeringCorrection, \
        GridDataFileReader, InterpolateGridDataCorrectionFromProvider, COLUMN_NAME_FOR_DRIVER_SETPOINT, \
        ModeSelectCorrection
    from ReflectometryServer.footprint_manager import FootprintSetup, BaseFootprintSetup
    from ReflectometryServer.geometry import PositionAndAngle, Position, ChangeAxis
    from ReflectometryServer.ioc_driver import IocDriver, PVWrapperForParameter
    from ReflectometryServer.out_of_beam import OutOfBeamPosition, OutOfBeamSequence
    from ReflectometryServer.parameters import InBeamParameter, AxisParameter, DirectParameter, \
        SlitGapParameter, EnumParameter, VirtualParameter
    from ReflectometryServer.pv_wrapper import MotorPVWrapper, JawsCentrePVWrapper, JawsGapPVWrapper, PVWrapper
    from ReflectometryServer.config_helper import ConfigHelper, get_configured_beamline, add_constant, add_component, \
        add_parameter, add_mode, add_driver, add_slit_parameters, add_beam_start, add_footprint_setup, \
        add_component_marker, add_driver_marker, add_parameter_marker, optional_is_set, as_mode_correction
