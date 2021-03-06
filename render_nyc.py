import math
import mapnik
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument(
  "--format",
  dest="format",
  help="file format"
)
args = parser.parse_args()

# Load the outline of the city from a GeoJSON file.
outline = None
with open("outline.geojson") as f:
  outline = f.read()

# Helpers to convert from lat/lon to web mercator. From:
# https://wiki.openstreetmap.org/wiki/Mercator#Python_implementation
def merc_x(lon):
  r_major = 6378137.000
  return r_major * math.radians(lon)

def merc_y(lat):
  if lat > 89.5:
    lat = 89.5
  if lat < -89.5:
    lat = -89.5
  r_major = 6378137.000
  r_minor = 6356752.3142
  temp = r_minor / r_major
  eccent = math.sqrt(1 - temp ** 2)
  phi = math.radians(lat)
  sinphi = math.sin(phi)
  con = eccent * sinphi
  com = eccent / 2
  con = ((1.0 - con) / (1.0 + con)) ** com
  ts = math.tan((math.pi / 2 - phi) / 2) / con
  y = 0 - r_major*math.log(ts)
  return y

# Compute the bounds.
top_left_lon = -74.06
top_left_lat = 41.12
bottom_right_lon = -73.90
bottom_right_lat = 40.85
box_coords = [
  merc_x(bottom_right_lon),
  merc_y(bottom_right_lat),
  merc_x(top_left_lon),
  merc_y(top_left_lat),
]
bounds = mapnik.Box2d(*box_coords)

# Create the map.
factor = 4 # higher for higher res
m = mapnik.Map(1024*factor, 2048*factor)
m.background = mapnik.Color("#FFFFFF")
m.aspect_fix_mode = mapnik.aspect_fix_mode.ADJUST_BBOX_HEIGHT
m.zoom_to_box(bounds)

# Create the style.
s = mapnik.Style()
r = mapnik.Rule()
line_symbolizer = mapnik.LineSymbolizer()
line_symbolizer.stroke_width = 1.95
r.symbols.append(line_symbolizer)
s.rules.append(r)
m.append_style("basic_style", s)

# Create the layer.
layer = mapnik.Layer("osm_lines")
query = (
"""
(
  SELECT *
  FROM (
    (
      SELECT *
      FROM planet_osm_polygon
      WHERE waterway = 'riverbank'
        AND tunnel IS NULL
      ORDER BY z_order
    )
    UNION ALL
    (
      SELECT *
      FROM planet_osm_line
      WHERE tunnel IS NULL
        AND bridge IS NULL
        AND highway IS NOT NULL
        AND ST_length(way) > 100
        AND highway IN (
          --'bridleway',
          --'bus_guideway',
          --'construction',
          'corridor',
          --'cycleway',
          --'disused',
          --'elevator',
          --'escalator',
          'footway',
          --'living_street',
          'motorway',
          'motorway_link',
          --'path',
          --'pedestrian',
          --'platform',
          'primary',
          --'primary_link',
          --'proposed',
          --'raceway',
          'residential',
          'road',
          'secondary',
          --'secondary_link',
          'service',
          --'steps',
          'tertiary',
          --'tertiary_link',
          --'track',
          'trunk',
          --'trunk_link',
          'unclassified',
          --'walkway',
          ' '
        )
      ORDER BY z_order
    )
  ) AS t
  WHERE ST_Intersects(
    t.way,
    ST_Transform(
      ST_SetSRID(
        ST_GeomFromGeoJSON('%s'),
        4326
      ),
      3857
    )
  )
)
AS shores_and_roads
"""
% outline
)
layer.datasource = mapnik.PostGIS(
    host="docker.for.mac.localhost",
    user="postgres",
    password="",
    dbname="osm_nyc",
    table=query,
)
layer.srs = "+init=epsg:4326"
layer.styles.append("basic_style")
m.layers.append(layer)

# Render!
print("Rendering...")
mapnik.render_to_file(m, "nyc." + args.format, args.format)
print("Rendered to `nyc.%s`." % args.format)
