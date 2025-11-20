import streamlit as st
import requests
import polyline
import folium
from streamlit.components.v1 import html
import random

# ---------------- CONFIGURATION ----------------
st.set_page_config(page_title="Smart Traffic Monitor", layout="wide")
st.title("🚦 Smart Real-Time Traffic Monitoring (India)")

# ✅ Your API Key (hardcoded)

API_KEY = "AIzaSyB_CRUKEm8sMnKVoEsUvmOAwozk28qILs4"

DEMO_MODE = False if API_KEY else True


# ---------------- DEMO DATA GENERATOR ----------------
def generate_demo_data(origin, destination, mode):
    """Generate demo traffic routes when API key not available"""
    routes = []
    colors = ["blue", "green", "purple", "orange", "red", "cadetblue"]

    start_lat, start_lng = 12.9716, 77.5946  # Bangalore
    end_lat, end_lng = 13.0827, 80.2707      # Chennai

    for i in range(random.randint(1, 3)):
        num_points = 20
        coords = []
        for j in range(num_points):
            frac = j / (num_points - 1)
            lat = start_lat + (end_lat - start_lat) * frac + random.uniform(-0.05, 0.05)
            lng = start_lng + (end_lng - start_lng) * frac + random.uniform(-0.05, 0.05)
            coords.append((lat, lng))

        base_duration = random.randint(1200, 7200)  # 20 mins to 2 hrs
        traffic_multiplier = random.uniform(1.1, 2.5)

        routes.append({
            "distance_text": f"{random.randint(50, 350)} km",
            "duration_text": f"{int(base_duration/60)} mins",
            "duration_in_traffic_text": f"{int(base_duration * traffic_multiplier / 60)} mins",
            "congestion_label": random.choice(["Low", "Moderate", "High"]),
            "coords": coords,
            "color": colors[i % len(colors)]
        })

    return routes


# ---------------- API CALL ----------------
def call_google_directions(api_key, origin, destination, mode="driving", alternatives=True):
    if not api_key:
        raise ValueError("Google Directions API key is missing.")

    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": api_key,
        "region": "in",
        "alternatives": str(alternatives).lower(),
        "departure_time": "now"
    }

    resp = requests.get(endpoint, params=params, timeout=15)
    data = resp.json()

    if data.get("status") != "OK":
        error_msg = data.get("error_message", f"API Error: {data.get('status')}")
        raise RuntimeError(f"Google Directions API error: {error_msg}")

    return data


# ---------------- HELPER ----------------
def assess_congestion(duration_seconds, duration_in_traffic_seconds):
    if not duration_in_traffic_seconds or not duration_seconds:
        return "N/A"
    increase = (duration_in_traffic_seconds - duration_seconds) / max(1, duration_seconds)
    pct = increase * 100

    if pct < 10:
        return "Low"
    elif pct < 40:
        return "Moderate"
    else:
        return "High"


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("ℹ️ About")
    st.info("This app shows real-time traffic congestion in India using Google Maps Directions API.")

    st.header("📖 How to Use")
    st.markdown("""
    1. Enter **start** and **destination**
    2. Choose travel mode
    3. Click **Get Routes**
    4. See map + congestion details
    """)


# ---------------- MAIN FORM ----------------
with st.form("route_form"):
    col1, col2 = st.columns(2)
    with col1:
        origin = st.text_input("Start Location", placeholder="e.g., MG Road, Bangalore")
    with col2:
        destination = st.text_input("Destination", placeholder="e.g., Majestic, Bangalore")

    mode = st.selectbox("Transport Mode", ["driving", "walking", "bicycling", "transit"])
    submitted = st.form_submit_button("Get Routes")


# ---------------- PROCESS REQUEST ----------------
if submitted:
    if not origin or not destination:
        st.error("❌ Please provide both start and destination.")
    else:
        with st.spinner("Fetching route information..."):
            try:
                if DEMO_MODE:
                    routes_out = generate_demo_data(origin, destination, mode)
                    map_center = (12.9716, 77.5946)
                    st.info("Demo data generated.")
                else:
                    data = call_google_directions(API_KEY, origin, destination, mode, alternatives=True)
                    routes_out = []
                    map_center = None
                    colors = ["blue", "green", "purple", "orange", "red", "cadetblue"]

                    for idx, r in enumerate(data.get("routes", [])):
                        leg = r.get("legs", [])[0]
                        distance_text = leg.get("distance", {}).get("text", "unknown")
                        duration_text = leg.get("duration", {}).get("text", "unknown")
                        duration_seconds = leg.get("duration", {}).get("value", 0)

                        duration_in_traffic_text = leg.get("duration_in_traffic", {}).get("text", "N/A")
                        duration_in_traffic_seconds = leg.get("duration_in_traffic", {}).get("value")

                        congestion_label = assess_congestion(duration_seconds, duration_in_traffic_seconds)
                        overview_poly = r.get("overview_polyline", {}).get("points")
                        coords = polyline.decode(overview_poly) if overview_poly else []

                        if not map_center and coords:
                            map_center = coords[len(coords)//2]

                        routes_out.append({
                            "distance_text": distance_text,
                            "duration_text": duration_text,
                            "duration_in_traffic_text": duration_in_traffic_text,
                            "congestion_label": congestion_label,
                            "coords": coords,
                            "color": colors[idx % len(colors)]
                        })

                # Show results
                st.success(f"✅ Found {len(routes_out)} route(s) from {origin} to {destination}")

                # Table
                st.subheader("📊 Route Information")
                table_data = []
                for i, r in enumerate(routes_out):
                    congestion_icon = "🟢" if r["congestion_label"] == "Low" else "🟡" if r["congestion_label"] == "Moderate" else "🔴"
                    table_data.append({
                        "Route": i+1,
                        "Distance": r["distance_text"],
                        "Duration": r["duration_text"],
                        "Traffic Duration": r["duration_in_traffic_text"],
                        "Congestion": f"{congestion_icon} {r['congestion_label']}"
                    })
                st.table(table_data)

                # Map
                if not map_center:
                    map_center = (20.5937, 78.9629)

                folium_map = folium.Map(location=map_center, zoom_start=10)
                for idx, route in enumerate(routes_out):
                    coords = route["coords"]
                    if coords:
                        folium.PolyLine(
                            coords,
                            weight=6,
                            color=route["color"],
                            popup=f"Route {idx+1}: {route['distance_text']} | {route['duration_text']} | {route['congestion_label']}"
                        ).add_to(folium_map)

                        if idx == 0:  # Add start & end markers
                            folium.Marker(coords[0], tooltip="Start", icon=folium.Icon(color="green")).add_to(folium_map)
                            folium.Marker(coords[-1], tooltip="End", icon=folium.Icon(color="red")).add_to(folium_map)

                st.subheader("🗺️ Map View")
                html(folium_map._repr_html_(), height=500)

                # Recommendation
                with st.expander("💡 Route Recommendation"):
                    def parse_duration_min(text):
                        try:
                            return float(text.split()[0])
                        except:
                            return float("inf")

                    best_route = min(
                        routes_out,
                        key=lambda x: (
                            0 if x["congestion_label"] == "Low" else 1 if x["congestion_label"] == "Moderate" else 2,
                            parse_duration_min(x["duration_text"])
                        )
                    )
                    st.success(f"⭐ Best Route: Route {routes_out.index(best_route) + 1}")
                    st.write(f"- Distance: {best_route['distance_text']}")
                    st.write(f"- Time: {best_route['duration_in_traffic_text']}")
                    st.write(f"- Congestion: {best_route['congestion_label']}")

            except Exception as e:
                st.error(f"Error: {str(e)}")

else:
    st.info("👆 Enter locations to get traffic updates.")
    india_map = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
    html(india_map._repr_html_(), height=400)
