import cadquery as cq
from math import sqrt, tan, pi

class SlewBearing:
    def __init__(self, inner_diameter, outer_diameter, width, roller_fit, roller_slide, num_rollers):
        # Layer adhesion is probably a limiting factor for the strength of the bearing
        # Points of failure are probably at 1/2 of width where there is the least amount of material
        # To ensure even load distribution at 1/2 of width, the area of an inner ring should be equal to the area of the outer ring
        # This way we eliminate the need to choose the pitch_diameter by ourselves

        # Since the bearing will be 3D printed, roller_diameter can be arbitrary
        # Roller_diameter depends on pitch_diameter and num_rollers
        # In order to reduce the number of less important variables, roller_diameter is calculated

        # Constraints
        ## 3d printer
        line_thickness = 0.4
        line_height = 0.2
        ## model
        inner_race_min_thickness = line_thickness * 3 # minimal number of walls for the inner race
        outer_race_min_thickness = line_thickness * 3 # minimal number of walls for the outer race
        roller_chamfer_min_length = line_thickness * 3 # minimal number of lines touching the print bed
        
        # Consistency check
        ## positive values
        if any(map(lambda x: x < 0.0, (inner_diameter, outer_diameter, width, roller_fit, roller_slide, num_rollers))):
            raise ValueError('Value can\'t be less than 0.0.')

        if num_rollers % 2 == 1:
            raise ValueError('The number of rollers must be divisible by 2.')

        roller_theta = pi/num_rollers # 360.0 / (num_rollers*2) to get an angle that a single roller occupies
        roller_diameter = sqrt(2.0)*sqrt((outer_diameter*outer_diameter + inner_diameter*inner_diameter)/(tan(roller_theta)**(-2.0)+4.0)) - roller_fit

        ## pitch_diameter real and more than 0.0
        if outer_diameter**2.0 + inner_diameter**2.0 - (roller_diameter + roller_fit)**2.0 <= 0.0:
            raise ValueError('Pitch diameter not real.')

        pitch_diameter = (sqrt(2.0)/2.0)*sqrt(outer_diameter**2.0 + inner_diameter**2.0 - (roller_diameter + roller_fit)**2.0)

        ## inner race as single piece
        if pitch_diameter - inner_diameter - (roller_diameter + roller_fit) * sqrt(2.0)/2.0 < inner_race_min_thickness:
            raise ValueError('Inner race min thickness too low. Consider decreasing inner diameter, increasing outer diameter, decreasing roller fit or increasing the number of rollers.')
        ## outer race as single piece
        if outer_diameter - pitch_diameter - (roller_diameter + roller_fit) * sqrt(2.0)/2.0 < outer_race_min_thickness:
            raise ValueError('Outer race min thickness too low. Consider increasing outer diameter, decreasing inner diameter, decreasing roller fit or increasing the number of rollers.')

        ## roller chamfer length
        if roller_diameter*sqrt(2.0) + roller_fit*sqrt(2.0)/2.0 - roller_slide*sqrt(2.0)/2.0 - width < roller_chamfer_min_length:
            raise ValueError('Roller chamfer too small. Consider increasing roller fit, decreasing roller slide, decreasing bearing width or decreasing the number of rollers.')

        # Parameters
        ## Races
        self.inner_diameter = inner_diameter # bore / ID of the bearing
        self.outer_diameter = outer_diameter # OD of the bearing
        self.pitch_diameter = pitch_diameter # diameter of the circle that that the rollers follow during rotation of a bearing
        self.width = width # bearing width
        ## Rollers
        self.roller_theta = roller_theta # an angle from the middle of the roller to it's tangent neighbour
        self.roller_diameter = roller_diameter # diameter of a roller
        self.roller_fit = roller_fit # tolerances between races and rolling part of a roller
        self.roller_length = roller_diameter + roller_fit - roller_slide # length of a roller
        self.roller_slide = roller_slide # tolerances between races and sliding part of a roller
        self.num_rollers = num_rollers 
        
        ## model parts
        self.assy = cq.Assembly()
        self.model = self.makeRacesOG()
        self.races = self.makeRaces()
        self.roller = self.makeRoller()
        

    def make(self):
        # Create the rollers
        roller = cq.Workplane('XY').circle(self.roller_diameter / 2).extrude(self.roller_length)
        rollers = []
        for i in range(self.num_rollers):
            angle = 360 / self.num_rollers * i
            roller_instance = roller.rotate((0, 0, 0), (0, 0, 1), angle).translate((0, (self.outer_diameter + self.inner_diameter) / 4, 0))
            rollers.append(roller_instance)


        return bearing


    def makeRaces(self):
        races = (
            cq.Workplane("YZ")
            .transformed(offset=(-self.outer_diameter, 0.0, 0.0))
            # outer and inner races combined (cut later)
            .rect(self.outer_diameter-self.inner_diameter, self.width, centered=False)
            .revolve(axisStart=(self.outer_diameter, 0.0, 0.0),
                     axisEnd=  (self.outer_diameter, 1.0, 0.0))
            # move to the center of rollers
            .center(self.outer_diameter-self.pitch_diameter,
                    self.width/2.0)
            # cut bearing surfaces
            .polyline([(-((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0, 0.0),
                       (0.0, ((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0),
                       (((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0, 0.0),
                       (0.0, -((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0)
                       ]).close()
            .revolve(axisStart=(self.pitch_diameter, 0.0, 0.0),
                     axisEnd=  (self.pitch_diameter, 1.0, 0.0),
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
    
    def makeBearing(self):
        self.assy.add(
            self.races,
            name="races",
            color=cq.Color("gold")
            )
        # for
        self.assy.add(
            self.roller
            # rotate roller
            .rotate(axisStartPoint=(0.0, 0.0, 0.0),
                    axisEndPoint=(1.0, 0.0, 0.0),
                    angleDegrees=45.0)
            # move to base position
            .translate(vec=(-100.0, 0.0, 0.0))
            # rotate to final position
            .rotate(axisStartPoint=(0.0, 0.0, 0.0),
                    axisEndPoint=(0.0, 0.0, 1.0),
                    angleDegrees=45.0),
            name="roller0",
            color=cq.Color("tan1") # tan3 for other way
            )
        return self.assy

    def makeRacesOG(self):
        side_section = (
            cq.Workplane("YZ")
            .transformed(offset=(-self.outer_diameter, 0.0, 0.0))
            # outer and inner races combined (cut later)
            .rect(self.outer_diameter-self.inner_diameter, self.width, centered=False)
            .revolve(axisStart=(self.outer_diameter, 0.0, 0.0),
                     axisEnd=  (self.outer_diameter, 1.0, 0.0))
            # move to the center of rollers
            .center(self.outer_diameter-self.pitch_diameter,
                    self.width/2.0)
            # cut bearing surfaces
            .polyline([(-((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0, 0.0),
                       (0.0, ((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0),
                       (((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0, 0.0),
                       (0.0, -((self.roller_diameter+self.roller_fit)*sqrt(2.0))/2.0)
                       ]).close()
            .revolve(axisStart=(self.pitch_diameter, 0.0, 0.0),
                     axisEnd=  (self.pitch_diameter, 1.0, 0.0),
                     combine='cut')
            #add a roller
            .transformed(rotate=(0.0, 0.0, -45.0))
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
        return side_section


# Create an instance of the SlewBearing
# based on https://www.ldb-bearing.com/slewing-bearings/cross-roller-bearing
my_bearing = SlewBearing(
    inner_diameter=234,
    outer_diameter=403.5,
    width=45,
#    roller_diameter=38.9,
    roller_fit=1.1,
    roller_slide=1.5,
    num_rollers=52.0
)

#bearing_geometry = my_bearing.model
bearing_geometry = my_bearing.makeBearing()

# Generate the bearing geometry
#bearing_geometry = my_bearing.make()

# Display the bearing (assuming you have a display function available)
show_object(bearing_geometry)