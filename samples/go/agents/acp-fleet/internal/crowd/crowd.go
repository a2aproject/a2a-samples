// Package crowd simulates users who work with their agents through the load
// balancer, and checks after every few turns that each agent still knows
// what its user told it and still has the files it wrote.
package crowd

import (
	"context"
	"crypto/rand"
	"errors"
	"fmt"
	"io"
	"math/big"
	"strings"
	"sync"
	"time"

	"github.com/a2aproject/a2a-go/v2/a2a"
	"github.com/a2aproject/a2a-go/v2/a2aclient"
	"github.com/a2aproject/a2a-go/v2/log"
	"github.com/a2aproject/a2a-samples/samples/go/agents/acp-fleet/internal/events"
)

// Names are the names of the users, in order.
var Names = []string{"alice", "bob", "carol", "dave", "erin", "frank", "grace", "heidi", "ivan", "judy", "mallory", "niaj", "olivia", "peggy", "rupert", "sybil"}

var words = []string{"amber", "basalt", "cobalt", "dune", "ember", "fjord", "garnet", "harbor", "indigo", "juniper", "kelp", "lagoon", "marble", "nectar", "onyx", "prairie", "quartz", "russet", "saffron", "tundra", "umber", "violet", "willow", "zephyr"}

const (
	pollInterval = time.Second
	turnTimeout  = 5 * time.Minute
	retryWait    = 2 * time.Second
)

// Config configures [Run].
type Config struct {
	// URL is the load balancer's URL.
	URL string
	// Users is the number of users, at most len(Names).
	Users int
	// Think is the longest pause of a user between turns.
	Think time.Duration
	// Events publishes the checks; nil drops them.
	Events *events.Publisher
	// Out gets a line for every turn.
	Out io.Writer
}

// Run runs the users until ctx ends.
func Run(ctx context.Context, cfg Config) error {
	if cfg.Users < 1 || cfg.Users > len(Names) {
		return fmt.Errorf("users must be between 1 and %d", len(Names))
	}
	client, err := a2aclient.NewFromEndpoints(ctx, []*a2a.AgentInterface{a2a.NewAgentInterface(cfg.URL, a2a.TransportProtocolHTTPJSON)})
	if err != nil {
		return err
	}
	defer func() {
		if err := client.Destroy(); err != nil {
			log.Warn(ctx, "closing the client failed", "cause", err)
		}
	}()
	var out sync.Mutex
	var wg sync.WaitGroup
	for i := range cfg.Users {
		u := &user{cfg: cfg, client: client, name: Names[i], out: &out, contextID: a2a.NewContextID()}
		wg.Go(func() {
			sleep(ctx, time.Duration(i)*700*time.Millisecond)
			u.run(ctx)
		})
	}
	wg.Wait()
	return nil
}

type user struct {
	cfg       Config
	client    *a2aclient.Client
	name      string
	out       *sync.Mutex
	contextID string

	code  string
	steps []string
}

func (u *user) file() string { return u.name + ".md" }

func (u *user) run(ctx context.Context) {
	u.code = strings.ToUpper(pick(words)) + "-" + fmt.Sprint(1000+randN(9000))
	first := pick(words)
	u.steps = []string{first}
	u.turn(ctx, "start "+u.file(), fmt.Sprintf("Hi, I'm %s. Remember this code, I'll ask for it later: %s. "+
		"Then create the file %s in the current directory with one line: step 1: %s. Reply in one short sentence.",
		u.name, u.code, u.file(), first), "", "")
	for n := 0; ctx.Err() == nil; n++ {
		sleep(ctx, time.Duration(1+randN(int(u.cfg.Think/time.Second)))*time.Second)
		switch n % 3 {
		case 0:
			word := pick(words)
			u.steps = append(u.steps, word)
			u.turn(ctx, fmt.Sprintf("step %d: %s", len(u.steps), word), fmt.Sprintf("Append the line \"step %d: %s\" to %s. Reply in one short sentence.", len(u.steps), word, u.file()), "", "")
		case 1:
			u.turn(ctx, "code?", "What is the code I asked you to remember? Reply with the code only.", "code", u.code)
		case 2:
			last := u.steps[len(u.steps)-1]
			u.turn(ctx, "last line?", fmt.Sprintf("Read %s and reply with the word on its last line only.", u.file()), "file", last)
		}
	}
}

// turn sends text until a task for it completes, and checks the reply for
// want. label names the turn in the output.
func (u *user) turn(ctx context.Context, label, text, check, want string) {
	for ctx.Err() == nil {
		task, err := u.send(ctx, text)
		if err != nil {
			u.log("%s: %v; sending again", label, err)
			sleep(ctx, retryWait)
			continue
		}
		switch task.Status.State {
		case a2a.TaskStateCompleted:
		case a2a.TaskStateFailed, a2a.TaskStateCanceled, a2a.TaskStateRejected:
			u.log("%s: %s, sending again", label, statusText(task))
			sleep(ctx, retryWait)
			continue
		default:
			u.log("%s: stopped in %s", label, task.Status.State)
			return
		}
		got := reply(task)
		if check == "" {
			u.log("%s → %s", label, short(got))
			return
		}
		ok := strings.Contains(strings.ToLower(got), strings.ToLower(want))
		mark := "✓"
		if !ok {
			mark = "✗"
		}
		if ok {
			u.log("%s %s %s", mark, label, want)
		} else {
			u.log("%s %s want %s, got %q", mark, label, want, short(got))
		}
		u.cfg.Events.Publish(ctx, events.Event{Kind: events.Checked, Context: u.contextID, User: u.name, Check: check, OK: ok})
		return
	}
}

// send sends text and polls the task through the load balancer until it ends
// or asks a question, which it answers with "once".
func (u *user) send(ctx context.Context, text string) (*a2a.Task, error) {
	ctx, cancel := context.WithTimeout(ctx, turnTimeout)
	defer cancel()
	msg := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart(text))
	msg.ContextID = u.contextID
	msg.Metadata = map[string]any{"user": u.name}
	res, err := u.client.SendMessage(ctx, &a2a.SendMessageRequest{Message: msg, Config: &a2a.SendMessageConfig{ReturnImmediately: true}})
	if err != nil {
		return nil, err
	}
	task, ok := res.(*a2a.Task)
	if !ok {
		return nil, fmt.Errorf("got %T, want a task", res)
	}
	for {
		switch {
		case task.Status.State.Terminal():
			return task, nil
		case task.Status.State == a2a.TaskStateInputRequired:
			answer := a2a.NewMessage(a2a.MessageRoleUser, a2a.NewTextPart("once"))
			answer.ContextID, answer.TaskID = u.contextID, task.ID
			answer.Metadata = map[string]any{"user": u.name}
			if _, err := u.client.SendMessage(ctx, &a2a.SendMessageRequest{Message: answer, Config: &a2a.SendMessageConfig{ReturnImmediately: true}}); err != nil {
				return nil, fmt.Errorf("answering: %w", err)
			}
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(pollInterval):
		}
		next, err := u.client.GetTask(ctx, &a2a.GetTaskRequest{ID: task.ID})
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			return nil, err
		}
		if err != nil {
			continue
		}
		task = next
	}
}

func (u *user) log(format string, args ...any) {
	u.out.Lock()
	defer u.out.Unlock()
	if _, err := fmt.Fprintf(u.cfg.Out, "%-7s %s\n", u.name, fmt.Sprintf(format, args...)); err != nil {
		log.Warn(context.Background(), "writing the output failed", "cause", err)
	}
}

func reply(task *a2a.Task) string {
	var sb strings.Builder
	for _, art := range task.Artifacts {
		for _, p := range art.Parts {
			sb.WriteString(p.Text())
		}
	}
	return strings.TrimSpace(sb.String())
}

func statusText(task *a2a.Task) string {
	text := strings.ToLower(string(task.Status.State))
	if task.Status.Message != nil {
		text = events.Snippet(task.Status.Message)
	}
	if strings.Contains(text, "server running this conversation") {
		return "its server stopped"
	}
	return short(text)
}

func short(s string) string {
	s = strings.Join(strings.Fields(s), " ")
	if r := []rune(s); len(r) > 48 {
		return string(r[:47]) + "…"
	}
	return s
}

func pick(list []string) string { return list[randN(len(list))] }

func randN(n int) int {
	if n <= 0 {
		return 0
	}
	v, err := rand.Int(rand.Reader, big.NewInt(int64(n)))
	if err != nil {
		panic(err)
	}
	return int(v.Int64())
}

func sleep(ctx context.Context, d time.Duration) {
	select {
	case <-ctx.Done():
	case <-time.After(d):
	}
}
