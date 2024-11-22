import cadquery as cq
from math import sqrt, tan, pi

class SlewBearing:

    class NegativeValueError(ValueError):
        pass
    class OddRollerValueError(ValueError):
        pass
    class PitchRadiusValueError(ValueError):
        pass
    class InnerRaceValueError(ValueError):
        pass
    class OuterRaceValueError(ValueError):
        pass
    class RollerChamferValueError(ValueError):
        pass

    
    def __init__(self, outer_diameter, inner_diameter, width, roller_fit, roller_slide, num_rollers):
        # Layer adhesion is probably a limiting factor for the strength of the bearing
        # Points of failure are probably at 1/2 of width where there is the least amount of material
        # To ensure even load distribution at 1/2 of width, the area of an inner ring should be equal to the area of the outer ring
        # This way we eliminate the need to choose the pitch_radius by ourselves

        # Since the bearing will be 3D printed, roller_diameter can be arbitrary
        # Roller_diameter depends on pitch_radius and num_rollers
        # In order to reduce the number of less important variables, roller_diameter is calculated

        # Constraints
        ## 3d printer
        line_thickness = 0.4
        line_height = 0.2
        ## model
        inner_race_min_thickness = line_thickness * 3 # minimal number of walls for the inner race
        outer_race_min_thickness = line_thickness * 3 # minimal number of walls for the outer race
        roller_chamfer_min_length = line_thickness * 3 # minimal number of lines touching the print bed
        outer_race_chamfer = line_thickness * 1 # chamfer to put on the outside of the races
        inner_race_chamfer = line_height * 1 # not really a chamfer but how deep to break an edge on the inside of the races
        outer_radius = outer_diameter/2.0 # it's more natural to provide ID and OD than using radii
        inner_radius = inner_diameter/2.0

        # Consistency check
        ## positive values
        if any(map(lambda x: x < 0.0, (inner_radius, outer_radius, width, roller_fit, roller_slide, num_rollers))):
            raise SlewBearing.NegativeValueError('Value can\'t be less than 0.0.')

        if num_rollers % 2 == 1:
            raise SlewBearing.OddRollerValueError('The number of rollers must be divisible by 2.')

        roller_theta_rad = pi/num_rollers # 360.0 / (num_rollers*2) to get an angle that a single roller occupies
        roller_theta_deg = 360.0 / (num_rollers*2.0) # for use later
        roller_diameter = sqrt(2.0)*sqrt((outer_radius*outer_radius + inner_radius*inner_radius)/(tan(roller_theta_rad)**(-2.0)+4.0)) - roller_fit

        ## pitch_radius real and more than 0.0
        if outer_radius**2.0 + inner_radius**2.0 - (roller_diameter + roller_fit)**2.0 <= 0.0:
            raise SlewBearing.PitchRadiusValueError('Pitch radius not real.')

        pitch_radius = (sqrt(2.0)/2.0)*sqrt(outer_radius**2.0 + inner_radius**2.0 - (roller_diameter + roller_fit)**2.0)

        ## inner race as single piece
        if pitch_radius - inner_radius - (roller_diameter + roller_fit) * sqrt(2.0)/2.0 < inner_race_min_thickness:
            raise SlewBearing.InnerRaceValueError('Inner race min thickness too low. Consider decreasing inner diameter, increasing outer diameter, decreasing roller fit or increasing the number of rollers.')
        ## outer race as single piece
        if outer_radius - pitch_radius - (roller_diameter + roller_fit) * sqrt(2.0)/2.0 < outer_race_min_thickness:
            raise SlewBearing.OuterRaceValueError('Outer race min thickness too low. Consider increasing outer diameter, decreasing inner diameter, decreasing roller fit or increasing the number of rollers.')

        ## roller chamfer length
        roller_chamfer_length = roller_diameter*sqrt(2.0) + roller_fit*sqrt(2.0)/2.0 - roller_slide*sqrt(2.0)/2.0 - width
        if roller_chamfer_length < roller_chamfer_min_length:
            raise SlewBearing.RollerChamferValueError('Roller chamfer too small. Consider increasing roller fit, decreasing roller slide, decreasing bearing width or decreasing the number of rollers.')

        # Parameters
        ## Races
        self.inner_diameter = inner_diameter # ID
        self.inner_radius = inner_radius # ID/2.0 of the bearing
        self.outer_diameter = outer_diameter # OD
        self.outer_radius = outer_radius # OD/2.0 of the bearing
        self.pitch_radius = pitch_radius # radius of the circle that that the rollers follow during rotation of a bearing
        self.width = width # bearing width
        self.outer_race_chamfer = outer_race_chamfer # chamfer to put on the outside of the races
        self.inner_race_chamfer = inner_race_chamfer # # not really a chamfer but how deep to break an edge on the inside of the races

        ## Rollers
        self.roller_theta = roller_theta_deg # an angle from the middle of the roller to it's tangent neighbour
        self.roller_diameter = roller_diameter # diameter of a roller
        self.roller_fit = roller_fit # tolerances between races and rolling part of a roller
        self.roller_length = roller_diameter + roller_fit - roller_slide # length of a roller
        self.roller_slide = roller_slide # tolerances between races and sliding part of a roller
        self.num_rollers = num_rollers # number of the rollers - it needs to be divisible by two
        self.roller_chamfer_length = roller_chamfer_length # length of the chamfer on the roller when viewing from the side
        
        ## model parts
        self.races = self.makeRaces()
        self.roller = self.makeRoller()
        self.assy = self.makeBearingAssembly()


    def makeRaces(self):
        races = (
            cq.Workplane("YZ")
            .transformed(offset=(-self.outer_radius, 0.0, 0.0))
            # outer and inner races combined (cut later)
            .rect(self.outer_radius-self.inner_radius, self.width, centered=False)
            .revolve(axisStart=(self.outer_radius, 0.0, 0.0),
                     axisEnd=  (self.outer_radius, 1.0, 0.0))
            # move to the center of rollers
            .center(self.outer_radius-self.pitch_radius,
                    self.width/2.0)
            # cut bearing surfaces
            .polyline([(-((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0, 0.0),
                       (0.0, ((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0),
                       (((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0, 0.0),
                       (0.0, -((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0)
                       ]).close()
            .revolve(axisStart=(self.pitch_radius, 0.0, 0.0),
                     axisEnd=  (self.pitch_radius, 1.0, 0.0),
                     combine='cut')
            # add a chamfer on OD and ID
            .faces(cq.NearestToPointSelector((0,0,self.width/2.0)))
            .chamfer(self.outer_race_chamfer)
            .faces(cq.NearestToPointSelector((0,self.outer_radius,self.width/2.0)))
            .chamfer(self.outer_race_chamfer)
            # break the edge between races
            .center(0.0,
                    0.0)
            .rect(((self.roller_fit+self.roller_slide)*sqrt(2.0)/2.0+self.roller_chamfer_length)+self.inner_race_chamfer*2.0, self.width, centered=True)
            .revolve(axisStart=(self.pitch_radius, 0.0, 0.0),
                     axisEnd=  (self.pitch_radius, 1.0, 0.0),
                     combine='cut')
        )
        return races
    
    def makeRoller(self):
        roller = (
            cq.Workplane("YZ")
            .polyline([(0.0, -self.roller_length/2.0),
                   ((self.width*sqrt(2.0)-self.roller_length)/2.0, -self.roller_length/2.0),
                   (self.roller_diameter/2.0, -(self.width*sqrt(2.0)-self.roller_diameter)/2.0),
                   #(self.roller_diameter/2.0, 0.0)
                   (self.roller_diameter/2.0, (self.width*sqrt(2.0)-self.roller_diameter)/2.0),
                   ((self.width*sqrt(2.0)-self.roller_length)/2.0, self.roller_length/2.0),
                   (0.0, self.roller_length/2.0)
                   ]).close()
            .revolve(axisStart=(0.0, 0.0, 0.0),
                     axisEnd=  (0.0, 1.0, 0.0))
        )
        return roller
    
    def makeBearingAssembly(self):
        assy = cq.Assembly()
        assy.add(
            self.races,
            name="races",
            color=cq.Color("gold")
            )
        for i in range(self.num_rollers):
            if i % 2 == 0:
                roller_rotate_deg = 45.0
                roller_colour = "tan1"
            else:
                roller_rotate_deg = -45.0
                roller_colour = "tan"

            assy.add(
                self.roller
                # rotate roller
                .rotate(axisStartPoint=(0.0, 0.0, 0.0),
                        axisEndPoint=(1.0, 0.0, 0.0),
                        angleDegrees=roller_rotate_deg)
                # move to base position
                .translate(vec=(0.0, -self.pitch_radius, self.width/2.0))
                # rotate to final position
                .rotate(axisStartPoint=(0.0, 0.0, 0.0),
                        axisEndPoint=(0.0, 0.0, 1.0),
                        angleDegrees=i*self.roller_theta*2.0),
                name="roller" + str(i),
                color=cq.Color(roller_colour)
                )
        return assy
    
    def exportAssyStl(self, folder):
        self.assy.toCompound().exportStl(folder 
                                         + "b" + str(self.outer_diameter) + "x" + str(self.inner_diameter) + "x" + str(self.width) 
                                         + "_" + str(self.roller_fit) + "x" + str(self.roller_slide) 
                                         + "_" + str(self.num_rollers) + ".stl")


# Create an instance of the SlewBearing
# based on https://www.ldb-bearing.com/slewing-bearings/cross-roller-bearing
sample_bearing = SlewBearing(
    outer_diameter=403.5,
    inner_diameter=234,
    width=45,
#    roller_diameter=38.9,
    roller_fit=1.1,
    roller_slide=1.5,
    num_rollers=24
)

show_object(sample_bearing.races)

sample_bearing.assy.toCompound().exportStl("models/bearing_test.stl")

OD = 200.0
#OD = 50.0
ID = 150.0
#ID = 15.0
W  = 20.0
#W  = 10.0
RF = 0.3
RS = 0.9
NR = 2

while True:
    try:
        SlewBearing(OD, ID, W, RF, RS, NR).exportAssyStl("models/")
    except SlewBearing.RollerChamferValueError as e:
        print("num_rollers=" + str(NR) + ": " + str(e))
        break
    except ValueError as e:
        print("num_rollers=" + str(NR) + ": " + str(e))
    finally:
        NR += 2

# Display the bearing
show_object(sample_bearing.assy)
