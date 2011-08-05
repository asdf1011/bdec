
OBJDIR=build
DISTDIR=dist
STATIC_LIB=$(DISTDIR)/lib${filename(protocol.name)}.a
EXECUTABLE= $(DISTDIR)/decode${filename(protocol.name)}
CFLAGS=-Wall -g
LDFLAGS=
MKDIR=mkdir -p

SRC=${' \\\n\t'.join('%s.c' % name for name in list(filename(e.name) for e in common) + ['variable_integer', 'buffer'])}
OBJS=$(patsubst %.c,$(OBJDIR)/%.o,$(SRC))

all: $(EXECUTABLE)

clean:
	rm -rf $(OBJDIR) $(DISTDIR)

$(EXECUTABLE): $(STATIC_LIB) $(OBJDIR)/main.o
	$(CC) $(LDFLAGS) -o $(EXECUTABLE) $(OBJS) $(OBJDIR)/main.o

$(STATIC_LIB): $(OBJS) | $(DISTDIR)
	$(AR) r $(STATIC_LIB) $(OBJS)

$(OBJDIR)/%.o: %.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c -o $@ $<

$(OBJDIR):
	$(MKDIR) $(OBJDIR)

$(DISTDIR):
	$(MKDIR) $(DISTDIR)
