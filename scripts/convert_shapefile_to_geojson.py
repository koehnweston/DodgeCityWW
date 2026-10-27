#!/usr/bin/env python3
"""
Center Pivot Shapefile-to-GeoJSON Converter & Pad Localizer
Incorporate Dodge City Verified Calibration Baseline Data:
- Manufacturer S/N corrections & swapped devices
- Physical riser tap heights above concrete slab
- Baseline totalizer readings and Unit A / B schedules
- Valve bank and booster station monitoring points
"""

import argparse
import json
import math
import os
import re
import sys
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon

# -----------------------------------------------------------------------------
# DODGE CITY REGISTRY: ONLY TRUE_SN AND TAG_SN
# Unit A: 0.001 * acre-feet (multiplier: 325.851429)
# Unit B: Gallons * 100     (multiplier: 100.0)
# -----------------------------------------------------------------------------
TRANSDUCER_REGISTRY = {
    "N-3":      {"true_sn": "53809", "tag_sn": "53809", "unit": "A", "base_reading": 295982, "tap_in": 76.0,  "flow_gpm": 700.0, "gauge_psi": 25.0, "notes": "Pivot On"},
    "N-2":      {"true_sn": "53746", "tag_sn": "53746", "unit": "B", "base_reading": 517580, "tap_in": 58.5,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "N-1":      {"true_sn": "53703", "tag_sn": "53703", "unit": "A", "base_reading": 544925, "tap_in": 132.0, "flow_gpm": 900.0, "gauge_psi": 27.0, "notes": "Pivot On"},
    "R-10":     {"true_sn": "53251", "tag_sn": "53251", "unit": "B", "base_reading": 405872, "tap_in": 82.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-9":      {"true_sn": "53235", "tag_sn": "53235", "unit": "B", "base_reading": 697579, "tap_in": 62.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-8":      {"true_sn": "53253", "tag_sn": "53764", "unit": "A", "base_reading": 256117, "tap_in": 132.0, "flow_gpm": None,  "gauge_psi": None, "notes": "Mismatched S/N"},
    "R-6":      {"true_sn": "53246", "tag_sn": "53246", "unit": "A", "base_reading": 598095, "tap_in": 76.0,  "flow_gpm": None,  "gauge_psi": None, "notes": "Worked on, ran later"},
    "R-7":      {"true_sn": "53252", "tag_sn": "53252", "unit": "A", "base_reading": 189843, "tap_in": 62.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-2":      {"true_sn": "53200", "tag_sn": "53200", "unit": "A", "base_reading": 832393, "tap_in": 62.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "N-5":      {"true_sn": "53248", "tag_sn": "53248", "unit": "A", "base_reading": 197062, "tap_in": 97.5,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "N-9":      {"true_sn": "53223", "tag_sn": "53223", "unit": "A", "base_reading": 203868, "tap_in": 80.5,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-1":      {"true_sn": "53224", "tag_sn": "53224", "unit": "A", "base_reading": 182493, "tap_in": 83.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "N-7":      {"true_sn": "53249", "tag_sn": "53249", "unit": "A", "base_reading": 555722, "tap_in": 57.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "N-6":      {"true_sn": "53754", "tag_sn": "53754", "unit": "A", "base_reading": 265028, "tap_in": 76.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "N-8":      {"true_sn": "51021", "tag_sn": "51021", "unit": "A", "base_reading": 181313, "tap_in": 83.0,  "flow_gpm": 500.0, "gauge_psi": 25.8, "notes": "Pivot On"},
    "R-4":      {"true_sn": "53706", "tag_sn": "53706", "unit": "A", "base_reading": 354833, "tap_in": 132.0, "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "N-4":      {"true_sn": "53755", "tag_sn": "53755", "unit": "A", "base_reading": 491381, "tap_in": 69.0,  "flow_gpm": 800.0, "gauge_psi": 35.0, "notes": "Pivot On"},
    "R-5 WEST": {"true_sn": "53764", "tag_sn": "53253", "unit": "A", "base_reading": 355371, "tap_in": 81.0,  "flow_gpm": None,  "gauge_psi": None, "notes": "Mismatched S/N"},
    "R-5 EAST": {"true_sn": "53250", "tag_sn": "53250", "unit": "A", "base_reading": 796361, "tap_in": 39.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-15":     {"true_sn": "53721", "tag_sn": "53721", "unit": "A", "base_reading": 80267,  "tap_in": 97.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-16":     {"true_sn": "53254", "tag_sn": "53254", "unit": "A", "base_reading": 602714, "tap_in": 76.5,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-14":     {"true_sn": "53704", "tag_sn": "53704", "unit": "A", "base_reading": 398894, "tap_in": 82.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-11":     {"true_sn": "53254", "tag_sn": "53213", "unit": "B", "base_reading": 647431, "tap_in": 76.0,  "flow_gpm": None,  "gauge_psi": None, "notes": "Mismatched S/N"},
    "R-12":     {"true_sn": "53195", "tag_sn": "53195", "unit": "A", "base_reading": 360108, "tap_in": 82.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "R-13":     {"true_sn": "51011", "tag_sn": "51011", "unit": "A", "base_reading": 340122, "tap_in": 48.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""},
    "NEWELL-1": {"true_sn": "53222", "tag_sn": "53222", "unit": "A", "base_reading": 456867, "tap_in": 30.0,  "flow_gpm": None,  "gauge_psi": None, "notes": ""}
}

STATIC_INFRASTRUCTURE = [
    {
        "id": "Booster Station - Suction",
        "true_sn": "53202",
        "tag_sn": "53202",
        "unit": "None",
        "base_reading": None,
        "tap_in": 0.0,
        "lat": 37.568544,
        "lon": -100.034103
    },
    {
        "id": "Booster Station - Discharge",
        "true_sn": "53241",
        "tag_sn": "53241",
        "unit": "None",
        "base_reading": None,
        "tap_in": 0.0,
        "lat": 37.568544,
        "lon": -100.034103
    },
    {
        "id": "Valve Bank btw R-14 and R-15",
        "true_sn": "53199",
        "tag_sn": "53199",
        "unit": "None",
        "base_reading": None,
        "tap_in": 37.0,
        "lat": 37.730000,
        "lon": -100.006250
    }
]


def normalize_id(val: str) -> str:
    if not val:
        return ""
    s = str(val).strip().upper()
    s = re.sub(r'([-_A-Z\s]|^)0+([1-9]\d*)', r'\1\2', s)
    s = re.sub(r'\s*-\s*', '-', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def calculate_true_pivot_center_planar(geom_planar) -> Point:
    if geom_planar.geom_type == 'MultiPolygon':
        geom_planar = max(geom_planar.geoms, key=lambda a: a.area)

    coords = list(geom_planar.exterior.coords)
    segments = []

    for i in range(len(coords) - 1):
        p1 = coords[i]
        p2 = coords[i + 1]
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        segments.append((dist, p1, p2))

    segments.sort(key=lambda x: x[0], reverse=True)
    if len(segments) < 3:
        return geom_planar.centroid

    longest_dist, l1_p1, l1_p2 = segments[0]
    second_longest_dist, l2_p1, l2_p2 = segments[1]
    perimeter = geom_planar.length

    if longest_dist > perimeter * 0.10 and second_longest_dist > perimeter * 0.10:
        pts1 = [l1_p1, l1_p2]
        pts2 = [l2_p1, l2_p2]
        for pA in pts1:
            for pB in pts2:
                if math.hypot(pA[0] - pB[0], pA[1] - pB[1]) < 1.0:
                    return Point(pA[0], pA[1])

    return geom_planar.centroid


def convert_shapefile(input_shp_path: str, output_geojson_path: str, name_col: str = None):
    print(f"Reading input shapefile: {input_shp_path}")
    gdf = gpd.read_file(input_shp_path)

    gdf = gdf[gdf.geometry.notnull() & gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])].copy()
    if gdf.empty:
        raise ValueError("No valid Polygon or MultiPolygon geometries found in file.")

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    if not name_col:
        cols = [c for c in gdf.columns if c.lower() != 'geometry']
        for candidate in ['NAME', 'FIELD_NAME', 'PIVOT_ID', 'ID', 'LABEL', 'PIVOT', 'IDENT']:
            matches = [c for c in cols if c.upper() == candidate]
            if matches:
                name_col = matches[0]
                break
        if not name_col:
            name_col = cols[0]

    gdf_planar = gdf.to_crs(epsg=3857)
    features = []

    # 1. Process Master Pivot Polygons
    for idx, row in gdf_planar.iterrows():
        raw_name = str(row.get(name_col, f"Pivot_{idx+1}")).strip()
        norm_key = normalize_id(raw_name)

        center_pad_planar = calculate_true_pivot_center_planar(row.geometry)
        pad_wgs = gpd.GeoSeries([center_pad_planar], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]
        poly_wgs = gpd.GeoSeries([row.geometry], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]

        meta = TRANSDUCER_REGISTRY.get(norm_key, {
            "actual_sn": str(row.get("SN", "UNASSIGNED")),
            "tag_sn": str(row.get("SN", "UNASSIGNED")),
            "sn": str(row.get("SN", "UNASSIGNED")),
            "unit": "A",
            "unit_mult": 325.851429,
            "base_reading": 0,
            "tap_in": 78.0,
            "flow_gpm": None,
            "gauge_psi": None,
            "notes": ""
        })

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(pad_wgs.x, 7), round(pad_wgs.y, 7)]
            },
            "properties": {
                "id": raw_name,
                "norm_id": norm_key,
                "true_sn": meta["true_sn"],
                "tag_sn": meta["tag_sn"],
                "unit": meta["unit"],
                "base_reading": meta["base_reading"],
                "tap_in": meta["tap_in"],
                "notes": meta.get("notes", ""),
                "polygon_geometry": poly_wgs.__geo_interface__
            }
        })

    # 2. Append Static Infrastructure
    for asset in STATIC_INFRASTRUCTURE:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(asset["lon"], 7), round(asset["lat"], 7)]
            },
            "properties": {
                "id": asset["id"],
                "norm_id": normalize_id(asset["id"]),
                "sn": asset["sn"],
                "actual_sn": asset["actual_sn"],
                "tag_sn": asset["actual_sn"],
                "unit": asset["unit"],
                "unit_mult": asset["unit_mult"],
                "base_reading": asset["base_reading"],
                "tap_in": asset["tap_in"],
                "baseline_flow_gpm": None,
                "baseline_gauge_psi": None,
                "notes": asset["notes"],
                "asset_type": asset["asset_type"],
                "polygon_geometry": None
            }
        })

    geojson_payload = {
        "type": "FeatureCollection",
        "features": features
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_geojson_path)), exist_ok=True)
    with open(output_geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_payload, f, indent=2)

    print(f"Successfully processed {len(features)} Dodge City assets with verified field data.")
    print(f"Saved to: {output_geojson_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Pivot Shapefile to GeoJSON with True Pad Extraction")
    parser.add_argument("-i", "--input", required=True, help="Path to input shapefile (.shp) or GeoPackage (.gpkg)")
    parser.add_argument("-o", "--output", default="data/default_pivots.geojson", help="Output GeoJSON path")
    parser.add_argument("-n", "--name-field", default=None, help="Column name containing Pivot ID")

    args = parser.parse_args()
    convert_shapefile(args.input, args.output, args.name_field)
