// x-run: gcc -lraylib -lm % -o %.elf && ./%.elf self

#include <fcntl.h>
#include <math.h>
#include <raylib.h> // https://github.com/raysan5/raylib / pacman -S raylib
#include <ctype.h>
#include <regex.h>
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
#define STB_DS_IMPLEMENTATION
#include <stb/stb_ds.h> // https://github.com/nothings/stb / pacman -S stb

#define panic(...) { \
  fprintf(stderr, "!PANIC! at %s:%d\n", __FILE__, __LINE__);\
  fprintf(stderr, __VA_ARGS__); \
  fprintf(stderr, "\nerrno=%d (%s)\n", errno, strerror(errno)); \
  abort(); \
}

#define LEN(X) (sizeof(X) / sizeof(X[0]))

#define FPS 60
#define WIDTH 512
#define HEIGHT 256
#define SCALE 2
#define PAGE_SIZE WIDTH * HEIGHT
#define SCREEN_WIDTH WIDTH * SCALE
#define SCREEN_HEIGHT HEIGHT * SCALE

enum { SCRTYPE_NONE, SCRTYPE_JUMP, SCRTYPE_SELECTION, SCRTYPE_HEXDUMP };

struct {
  int screen, key;
} screen_key_mapping[] = {
  { SCRTYPE_JUMP, KEY_J },
  { SCRTYPE_HEXDUMP, KEY_X },
  { SCRTYPE_SELECTION, KEY_S },
};

struct memory_area {
  char name[256], permissions[4];
  size_t start, length;
};

struct colored_line {
  Color color; char *text;
};

static struct {
  int pressed, released;
} key_timings[512];

void update_keys(int frame);
bool is_key_held(int key, int frame, int threshold);
void reload_memory_mapping(struct memory_area **arr, const char *map_file);

int main(int argc, char **argv) {

  /*u_int8_t *mem_curr = malloc(PAGE_SIZE), *mem_prev = malloc(PAGE_SIZE);*/
  /*memset(mem_curr, 0, PAGE_SIZE);*/
  /*memset(mem_prev, 0, PAGE_SIZE);*/
  static u_int8_t mem_curr[PAGE_SIZE], mem_prev[PAGE_SIZE];

  struct memory_area *memory_map = NULL;

  reload_memory_mapping(&memory_map, TextFormat("/proc/%s/maps", argv[1]));
  int fd;
  {
    const char *filename = TextFormat("/proc/%s/mem", argv[1]);
    if ((fd = open(filename, O_RDONLY)) < 0) {
      panic("Failed to open %s", filename); 
    }
  }

  InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "");
  SetExitKey(KEY_NULL);
  Font font = LoadFont("./ic8x8u.ttf");
  SetTargetFPS(FPS);
  HideCursor();
  RenderTexture2D memory = LoadRenderTexture(WIDTH, HEIGHT);

  bool should_refresh = false;
  int current_screen = SCRTYPE_NONE, frames_since_switch = 0;
  size_t offset = memory_map[0].start;
  struct { size_t start, end; } selection = { 0 };

  int scr_jump_index = 0, scr_jump_window_start = 0;

  struct colored_line *debug_lines = NULL;

  for (int frame = 0; !WindowShouldClose(); frame++) {
    BeginDrawing();
    ClearBackground(BLACK);
    {
      update_keys(frame);

      // Screen switching
      if (current_screen != SCRTYPE_NONE && IsKeyPressed(KEY_ESCAPE)) {
        current_screen = SCRTYPE_NONE;
      }
      for (int i = 0; i < LEN(screen_key_mapping); i++) {
        if (IsKeyPressed(screen_key_mapping[i].key)) {
          if (current_screen == screen_key_mapping[i].screen) {
            current_screen = SCRTYPE_NONE;
            frames_since_switch = 0;
          } else {
            current_screen = screen_key_mapping[i].screen;
            frames_since_switch = 0;
          }
        }
      }

      {
        memset(mem_curr, 0, PAGE_SIZE);

        int failed_reads = 0;
        size_t total_bytes = 0;
        for (int i = 0; i < HEIGHT; i++) {
          size_t off = i * WIDTH;
          lseek(fd, offset + off, SEEK_SET);
          ssize_t n_read = read(fd, mem_curr + off, WIDTH);
          if (n_read < 0) {
            failed_reads++;
          } else {
            total_bytes += n_read;
          }
        }

        if (failed_reads) {
          struct colored_line line = {
            RED, strdup(TextFormat("Some reads failed (%d)", failed_reads))
          };
          arrput(debug_lines, line);
        }
        if (total_bytes < PAGE_SIZE) {
          struct colored_line line = {
            YELLOW, strdup(TextFormat("Underread: %zd/%zd", total_bytes, PAGE_SIZE))
          };
          arrput(debug_lines, line);
        }

        Color color = BLACK;
        BeginTextureMode(memory);
        for (int i = 0; i < PAGE_SIZE; i++) {
          if (mem_curr[i] != mem_prev[i] || should_refresh) {
            color.r = mem_curr[i];
            color.b = isprint(mem_curr[i]) ? 255 : 0;
            color.g = (i + offset) >= selection.start && (i + offset) <= selection.end ? 255 : 0;
            DrawPixel(i % WIDTH, i / WIDTH, color);
            mem_prev[i] = mem_curr[i];
          }
        }
        should_refresh = false;
        EndTextureMode();
      }

      // Drawing memory view
      DrawTexturePro(memory.texture,
          (Rectangle){ 0, 0, WIDTH, -HEIGHT },
          (Rectangle){ 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT },
          (Vector2){ 0, 0 }, 0, WHITE);

      switch (current_screen) {
        case SCRTYPE_JUMP:
          {
            DrawRectangle(4, 4, 520, 272, ColorAlpha(DARKGRAY, 0.7));
            DrawRectangle(4, 4, 520, 12, ColorAlpha(BLACK, 0.7));
            DrawRectangleLines(4, 4, 520, 272, frames_since_switch ? GRAY : RED);
            DrawRectangleLines(4, 4, 520, 12, frames_since_switch ? GRAY : RED);

            if (frames_since_switch == 0) {
              reload_memory_mapping(&memory_map, TextFormat("/proc/%s/maps", argv[1]));

              for (int i = 0; i < arrlen(memory_map); i++) {
                struct memory_area area = memory_map[i];
                if (offset >= area.start && offset <= area.start + area.length) {
                  scr_jump_index = i;
                }
              }
            }

            int old_i = scr_jump_index;

            scr_jump_index -= (int)GetMouseWheelMove();
            if (IsKeyPressed(KEY_DOWN)
                || is_key_held(KEY_DOWN, frame, 10) && (frame % 2 == 0)) {
              scr_jump_index++;
            }
            if (IsKeyPressed(KEY_UP)
                || is_key_held(KEY_UP, frame, 10) && (frame % 2 == 0)) {
              scr_jump_index--;
            }
            if (IsKeyPressed(KEY_PAGE_DOWN)) {
              scr_jump_index += 10;
            }
            if (IsKeyPressed(KEY_PAGE_UP)) {
              scr_jump_index -= 10;
            }

            if (scr_jump_index < 0) {
              scr_jump_index = 0;
            }

            if (scr_jump_index > arrlen(memory_map) - 1) {
              scr_jump_index = arrlen(memory_map) - 1;
            }

            if (old_i != scr_jump_index && IsKeyDown(KEY_LEFT_CONTROL)) {
              offset = memory_map[scr_jump_index].start;
            }

            if (scr_jump_index < scr_jump_window_start) {
              scr_jump_window_start = scr_jump_index;
            }

            if (scr_jump_index >= scr_jump_window_start + 32) {
              scr_jump_window_start = scr_jump_index - 31;
            }

            Vector2 pos = { 6, 6 };
            DrawTextEx(font, "MAPPED AREAS", pos, 8, 0, WHITE); pos.y += 10;

            for (int i = scr_jump_window_start, j = 0;
                i < scr_jump_window_start + 32 && j < frames_since_switch * 2;
                i++, j++) {
              struct memory_area area = memory_map[i];
              DrawTextEx(font,
                  TextFormat("%016lx %s %s", area.start, area.permissions, area.name), pos, 8, 0,
                  i == scr_jump_index ? RED : WHITE);
              pos.y += 8;
            }

            DrawLine(5, 275, 5 + (scr_jump_index + 1) * 518 / arrlen(memory_map), 275, GREEN);

            if (IsKeyPressed(KEY_ENTER)) {
              offset = memory_map[scr_jump_index].start;
              if (IsKeyUp(KEY_LEFT_CONTROL)) {
                current_screen = SCRTYPE_NONE;
              }
            }
          }
          break;

        case SCRTYPE_HEXDUMP:
          {
            Rectangle rec = { 4, 4, 512 + 8, 256 + 12 + 8 };
            Vector2 mouse = GetMousePosition();

            if (mouse.x >= rec.x && mouse.x <= (rec.x + rec.width))
              rec.x = SCREEN_WIDTH - 4 - rec.width;
            if (mouse.y >= rec.y && mouse.y <= (rec.y + rec.height))
              rec.y = SCREEN_HEIGHT - 4 - rec.height;

            DrawRectangleRec(rec, ColorAlpha(DARKGRAY, 0.7));
            DrawRectangleRec(rec, ColorAlpha(BLACK, 0.7));
            DrawRectangleLinesEx(rec, 1, frames_since_switch ? GRAY : RED);
            DrawRectangleLinesEx(rec, 1, frames_since_switch ? GRAY : RED);
            Vector2 pos = { rec.x + 2, rec.y + 2 };

            size_t mouse_offset = WIDTH * (mouse.y / SCALE);
            size_t cur_pos = (mouse.x / SCALE) + mouse_offset + offset;

            if (mouse.x < 0 || mouse.y < 0 || mouse.x > SCREEN_WIDTH || mouse.y >= SCREEN_HEIGHT) {
              mouse_offset = 0;
              cur_pos = offset;
            }

            char *wheretfami = "[wilderness]";
            for (int i = 0; i < arrlen(memory_map); i++) {
              struct memory_area area = memory_map[i];
              if (cur_pos >= area.start && cur_pos <= area.start + area.length) {
                wheretfami = area.name;
                break;
              }
            }

            DrawTextEx(font, TextFormat("HEXDUMP (cursor in %s)", wheretfami), pos, 8, 0, WHITE);

            for (int i = 0; i < 32; i++) {
              pos.x = rec.x + 2;
              pos.y = rec.y + 16 + i * 8;
              DrawTextEx(font, TextFormat("%p", offset + i * 16), pos, 8, 0, GRAY);
            }

            for (int i = 0; i < 512; i++) {
              pos.x = rec.x + 2 + 15 * 8 + (i % 16) * 16;
              pos.y = rec.y + 16 + (int)(i / 16) * 8;
              u_int8_t value = mem_curr[i + mouse_offset];
              Color color = ColorAlpha(BLACK, 0.5);
              color.r = value;
              color.g = i == (mouse.x / SCALE) ? 255 : 0;
              color.b = isprint(value) ? 255 : 0;
              DrawRectangle(pos.x, pos.y, 16, 8, color);
              DrawTextEx(font, TextFormat("%02x", value), pos, 8, 0, WHITE);

              pos.x = rec.x + 2 + 8 * 16 + 8 * 2 * 16 + (i % 16) * 8;
              DrawRectangle(pos.x, pos.y, 8, 8, color);
              if (isprint(value)) {
                DrawTextEx(font, TextFormat("%c", value), pos, 8, 0, WHITE);
              }
            }

          }
          goto screentype_none_case;
          break;

        case SCRTYPE_SELECTION:
          {
            Vector2 mouse = GetMousePosition();
            size_t i = offset + (size_t)(mouse.x / SCALE + (mouse.y / SCALE) * WIDTH);

            if (IsMouseButtonDown(MOUSE_BUTTON_LEFT) || IsMouseButtonPressed(MOUSE_BUTTON_LEFT)) {
              should_refresh = true;
              selection.start = i;
            }
            if (IsMouseButtonDown(MOUSE_BUTTON_RIGHT) || IsMouseButtonPressed(MOUSE_BUTTON_RIGHT)) {
              selection.end = i;
              should_refresh = true;
            }

            if (IsKeyPressed(KEY_P)) {
              selection.start &= ~0xfff;
              selection.end &= ~0xfff;
              should_refresh = true;
            }

            if (IsKeyPressed(KEY_W)) {
              static u_int8_t buffer[4096];
              FILE *fp = fopen("selection.data", "wb");
              if (fp) {
                printf("selection: %zd-%zd (%zd)\n",
                    selection.start, selection.end,
                    selection.end - selection.start);
                ssize_t pos = selection.start, len = selection.end - pos;
                do {
                  ssize_t remaining = selection.end - pos;
                  memset(buffer, 0, 4096);
                  if (remaining < 4096) {
                    lseek(fd, pos, SEEK_SET);
                    read(fd, buffer, remaining);
                    fwrite(buffer, 1, remaining, fp);
                  } else {
                    lseek(fd, pos, SEEK_SET);
                    read(fd, buffer, 4096);
                    fwrite(buffer, 1, 4096, fp);
                  }
                  pos += 4096;
                } while (pos < selection.end);
                fclose(fp);
              }
            }

            Vector2 pos = { 4, 4 };
            DrawTextEx(font, "SELECTION", pos, 8, 0, WHITE); pos.y += 8;
            DrawTextEx(font, TextFormat("%016lx", selection.start), pos, 8, 0, WHITE); pos.y += 8;
            DrawTextEx(font, TextFormat("%016lx", selection.end), pos, 8, 0, WHITE); pos.y += 8;
          }
          /* fallthrough */

        case SCRTYPE_NONE:
screentype_none_case:
          offset += WIDTH * (int)GetMouseWheelMove() * (IsKeyDown(KEY_LEFT_CONTROL) ? -20 : -2);
          if (IsKeyPressed(KEY_DOWN)
              || is_key_held(KEY_DOWN, frame, 10) && !(frame % 2)) {
            offset += WIDTH * 2;
          }
          if (IsKeyPressed(KEY_UP)
              || is_key_held(KEY_UP, frame, 10) && !(frame % 2)) {
            offset -= WIDTH * 2;
          }
          if (IsKeyPressed(KEY_PAGE_DOWN)
              || is_key_held(KEY_PAGE_DOWN, frame, 10) && !(frame % 2)) {
            offset += WIDTH * 16;
          }
          if (IsKeyPressed(KEY_PAGE_UP)
              || is_key_held(KEY_PAGE_UP, frame, 10) && !(frame % 2)) {
            offset -= WIDTH * 16;
          }
          if (IsKeyPressed(KEY_R)) {
            should_refresh = true;
          }
          if (IsKeyDown(KEY_ESCAPE)) {
            int wait_remaining = 60 - (frame - key_timings[KEY_ESCAPE].pressed);
            const char *txt = TextFormat("Exiting... %d", wait_remaining);
            for (int ox = -4; ox <= 4; ox++) {
              for (int oy = -4; oy <= 4; oy++) {
                DrawTextEx(font, txt, (Vector2){
                    36 + ox,
                    SCREEN_HEIGHT - 20 + oy
                  }, 16, 0, BLACK);
              }
            }
            DrawTextEx(font, txt, (Vector2){ 36, SCREEN_HEIGHT - 20 }, 16, 0, RED);
            DrawCircle(12, SCREEN_HEIGHT - 12, 10, BLACK);
            DrawCircleSector((Vector2){ 12, SCREEN_HEIGHT - 12 }, 8,
                0.0, 360. * (float)wait_remaining / 60., 30, RED);
            if (wait_remaining < 0) {
              goto exit;
            }
          }
          break;

        default:
          current_screen = SCRTYPE_NONE;
          break;
      }

      {
        Vector2 pos = { 2, 2 }, sz, tmp;
        for (int i = 0; i < arrlen(debug_lines); i++) {
          sz = MeasureTextEx(font, debug_lines[i].text, 8, 0);
          for (int ox = -1; ox <= 1; ox++) {
            for (int oy = -1; oy <= 1; oy++) {
              tmp.x = pos.x + ox; tmp.y = pos.y + oy;
              DrawTextEx(font, debug_lines[i].text, tmp, 8, 0, BLACK);
            }
          }
          DrawTextEx(font, debug_lines[i].text, pos, 8, 0, debug_lines[i].color);
          pos.y += sz.y;
        }
      }
    }

    {
      Vector2 mouse = GetMousePosition();
      DrawCircleLines(mouse.x, mouse.y, 5, WHITE);
    }
    EndDrawing();

    // cleanup
    for (int i = 0; i < arrlen(debug_lines); i++) {
      free(debug_lines[i].text);
    }
    arrfree(debug_lines);
    frames_since_switch++;
  }
exit:
  UnloadFont(font);
}

void reload_memory_mapping(struct memory_area **arr, const char *map_file) {
  char line[1024], tmp[256];
  regex_t regexp;
  if (regcomp(&regexp, "^([0-9a-f]+)-([0-9a-f]+) ([rxwp\\-]+) [0-9a-f]+ "
        "[0-9]+:[0-9]+ [0-9]+ [[:space:]]+ (.*)", REG_EXTENDED)) {
    panic("Failed to compile regexp");
  }

  regmatch_t matches[5];

  arrfree(*arr);

  FILE *fp = fopen(map_file, "r");
  if (!fp) { panic("Failed to open %s", map_file); }

  do {
    fgets(line, 1023, fp);
    char *nl = strstr(line, "\n");
    if (nl) *nl = '\0';

    struct memory_area area;
    if (!regexec(&regexp, line, 5, matches, 0)) {
      strncpy(tmp, line + matches[1].rm_so, matches[1].rm_eo - matches[1].rm_so);
      tmp[matches[1].rm_eo - matches[1].rm_so] = '\0';
      area.start = strtoull(tmp, NULL, 16);

      strncpy(tmp, line + matches[2].rm_so, matches[2].rm_eo - matches[2].rm_so);
      tmp[matches[2].rm_eo - matches[2].rm_so] = '\0';
      area.length = strtoull(tmp, NULL, 16) - area.start;

      strncpy(tmp, line + matches[3].rm_so, matches[3].rm_eo - matches[3].rm_so);
      tmp[matches[3].rm_eo - matches[3].rm_so] = '\0';
      strncpy(area.permissions, tmp, 4); area.permissions[3] = '\0';

      strncpy(tmp, line + matches[4].rm_so, matches[4].rm_eo - matches[4].rm_so);
      tmp[matches[4].rm_eo - matches[4].rm_so] = '\0';

      strncpy(area.name, tmp, 255);

      arrput(*arr, area);
    }
  } while (!feof(fp));
}

void update_keys(int frame) {
  for (int key = 0; key < 512; key++) {
    if (IsKeyPressed(key)) key_timings[key].pressed = frame;
    if (IsKeyReleased(key)) key_timings[key].released = frame;
  }
}

bool is_key_held(int key, int frame, int threshold) {
  return IsKeyDown(key) && frame - key_timings[key].pressed >= threshold;
}
