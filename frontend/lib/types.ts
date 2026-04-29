export interface TripSpec {
    origin: string;
    destination: string;
    dates: string;
    travelers: number;
    budget_tier: string;
    interests: string[];
    constraints: string[];
    travel_style: string;
}

export interface Activity {
    name: string;
    description: string;
    location: string;
    estimated_cost: number;
    booking_link?: string;
    time_slot: string;
}

export interface DailyPlan {
    day_number: number;
    date: string;
    city: string;
    weather?: {
        temperature_c: number;
        condition: string;
        precip_prob?: number;
    };
    morning_activities: Activity[];
    afternoon_activities: Activity[];
    evening_activities: Activity[];
    daily_transport_notes?: string;
    meal_suggestions: string[];
}

export interface AccommodationOption {
    name: string;
    area: string;
    price_per_night: number;
    rating?: number;
    description: string;
    booking_link?: string;
}

export interface TransportOption {
    type: string;
    provider: string;
    departure: string;
    arrival: string;
    estimated_price: number;
    booking_link?: string;
}

export interface TripPlan {
    trip_id?: string;
    title: string;
    summary: string;
    itinerary: DailyPlan[];
    hotels_shortlist: AccommodationOption[];
    intercity_travel: TransportOption[];
    budget: {
        flights: number;
        accommodation: number;
        activities: number;
        food: number;
        transport_local: number;
        total_estimated: number;
        currency: string;
    };
    packing_list: { category: string; item: string; reason?: string }[];
}
