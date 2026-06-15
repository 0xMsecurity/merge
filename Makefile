PYTHON  = python3

SRCDIR  = src
TESTDIR = tests
BINDIR  = bin

MERGE   = $(BINDIR)/merge
BIN1    = $(BINDIR)/bin1
BIN2    = $(BINDIR)/bin2
BIN3    = $(BINDIR)/bin3

.PHONY: all clean test

all: $(MERGE) $(BIN1) $(BIN2)

$(BINDIR):
	mkdir -p $(BINDIR)

$(MERGE): $(SRCDIR)/merge.py | $(BINDIR)
	cp $< $@
	chmod +x $@

$(BIN1): $(TESTDIR)/bin1.py | $(BINDIR)
	cp $< $@
	chmod +x $@

$(BIN2): $(TESTDIR)/bin2.py | $(BINDIR)
	cp $< $@
	chmod +x $@

test: all
	@echo "--- bin1 ---"
	./$(BIN1)
	@echo "--- bin2 ---"
	./$(BIN2)
	@echo "--- merge (no args) ---"
	./$(MERGE) || true
	@echo "--- merge bin1 bin2 -o bin3 ---"
	./$(MERGE) $(BIN1) $(BIN2) -o $(BIN3)
	@echo "--- bin3 ---"
	./$(BIN3)

clean:
	rm -rf $(BINDIR)
