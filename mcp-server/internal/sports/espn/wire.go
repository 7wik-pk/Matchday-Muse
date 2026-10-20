package espn

// The parts of ESPN's responses the adapter reads. The recorder re-encodes
// responses through these types, so testdata holds exactly these fields.

type scoreboard struct {
	Events []struct {
		ID           string        `json:"id"`
		Date         string        `json:"date"`
		Status       status        `json:"status"`
		Competitions []competition `json:"competitions"`
	} `json:"events"`
}

type competition struct {
	Date   string  `json:"date,omitempty"`
	Status *status `json:"status,omitempty"`
	Venue  struct {
		FullName string `json:"fullName,omitempty"`
	} `json:"venue"`
	Competitors []struct {
		HomeAway string `json:"homeAway"`
		Winner   bool   `json:"winner"`
		Score    string `json:"score"`
		Team     team   `json:"team"`
	} `json:"competitors"`
	Headlines []struct {
		Description string `json:"description"`
	} `json:"headlines,omitempty"`
}

type team struct {
	DisplayName      string `json:"displayName"`
	ShortDisplayName string `json:"shortDisplayName"`
	Abbreviation     string `json:"abbreviation"`
}

type status struct {
	Type struct {
		Name      string `json:"name"`
		State     string `json:"state"`
		Completed bool   `json:"completed"`
	} `json:"type"`
}

type summary struct {
	Header struct {
		ID           string        `json:"id"`
		Competitions []competition `json:"competitions"`
	} `json:"header"`
	GameInfo struct {
		Venue struct {
			FullName string `json:"fullName"`
		} `json:"venue"`
	} `json:"gameInfo"`
	Boxscore struct {
		Teams []boxTeam `json:"teams"`
	} `json:"boxscore"`
	KeyEvents  []play `json:"keyEvents,omitempty"`
	Commentary []struct {
		Text string `json:"text"`
		Play *play  `json:"play,omitempty"`
	} `json:"commentary,omitempty"`
	Article *struct {
		Headline    string `json:"headline"`
		Description string `json:"description"`
		Published   string `json:"published"`
	} `json:"article,omitempty"`
}

type boxTeam struct {
	Team       team `json:"team"`
	Statistics []struct {
		Name         string `json:"name"`
		DisplayValue string `json:"displayValue"`
	} `json:"statistics"`
}

type play struct {
	ID   string `json:"id"`
	Type struct {
		Type string `json:"type"`
	} `json:"type"`
	Text  string `json:"text,omitempty"`
	Clock struct {
		DisplayValue string `json:"displayValue"`
	} `json:"clock"`
	Team *struct {
		DisplayName string `json:"displayName"`
	} `json:"team,omitempty"`
	Participants []struct {
		Athlete struct {
			DisplayName string `json:"displayName"`
		} `json:"athlete"`
	} `json:"participants,omitempty"`
}
